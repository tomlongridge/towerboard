<?php

namespace App\Http\Controllers;

use App\Board;
use App\User;
use App\BoardSubscription;
use App\Http\Requests\EmailListRequest;

use Auth;
use Illuminate\Http\Request;
use App\Enums\SubscriptionType;
use App\Notifications\UserSubscribed;
use Illuminate\Support\Facades\Validator;
use Illuminate\Support\Facades\Mail;
use Illuminate\Support\Facades\URL;
use App\Mail\SubscriptionLink;

class SubscriptionController extends Controller
{
    /**
     * Subscribes an authenticated user.
     *
     * @param  \Illuminate\Http\Request  $request
     * @param  \App\Board                $board the board to subscribe to
     * @param  \App\User                 $user the user to subscribe
     * @return \Illuminate\Http\Response
     */
    public function store(Request $request, Board $board, User $user)
    {
        if (!isset($user->id)) {
            $user = Auth::user();
        }

        $this->authorize('create', [BoardSubscription::class, $board, $user]);

        $board->subscribers()->attach($user->id);
        $request->session()->flash('success', 'You have been subscribed to this board.');

        return back();
    }

    /**
     * Changes the subscription type of an authenticated user.
     *
     * @param  \Illuminate\Http\Request  $request
     * @param  \App\Board                $board the board to subscribe to
     * @param  \App\User                 $user the user to amend
     * @return \Illuminate\Http\Response
     */
    public function update(Request $request, Board $board, User $user)
    {
        if (!isset($user->id)) {
            $user = Auth::user();
        }

        $this->authorize('update', [BoardSubscription::class, $board, $user]);

        $board->subscribers()->updateExistingPivot(
            $user->id,
            ['type' => SubscriptionType::getInstance(intval($request->type))]
        );
        return back();
    }

    /**
     * Subscribes a list of email addresses to a board.
     *
     * @param  \App\Board                            $board the board to subscribe to
     * @param  \App\Http\Requests\EmailListRequest   $request the email addresses to add
     * @return \Illuminate\Http\Response
     */
    public function bulkAdd(Board $board, EmailListRequest $request)
    {
        $this->authorize('addUser', [BoardSubscription::class, $board, Auth::user()]);

        $numCreated = 0;
        $numSubscribed = 0;
        foreach ($request->emails as $email) {
            $user = User::where('email', $email["email"])->first();
            if ($user == null) {
                $user = User::create([
                    'email' => $email["email"],
                    'forename' => $email["forename"],
                    'surname' => $email["surname"],
                ]);
                $numCreated++;
            }

            if (!$board->subscribers()->where('id', $user->id)->exists()) {
                $board->subscribers()->attach($user->id);
                $user->notify(new UserSubscribed($board, $user, auth()->user()));
                $numSubscribed++;
            }
        }

        if ($numSubscribed == 0) {
            $request->session()->flash('warning', 'No new users added.');
        } else {
            $numSubscribed -= $numCreated;
            $request->session()->flash(
                'success',
                "Subscribed $numCreated user(s)" .
                ($numSubscribed > 0 ? "and subscribed $numSubscribed existing users." : ".")
            );
        }

        return redirect(route('boards.members', ['board' => $board->name]));
    }

    /**
     * Subscribes a user from a signed URL.
     *
     * @param  \Illuminate\Http\Request  $request
     * @param  \App\Board                $board the board to subscribe to
     * @param  String                    $email the email address to use
     * @return \Illuminate\Http\Response
     */
    public function add(Request $request, Board $board, String $email)
    {
        if (!$request->hasValidSignature()) {
            abort(401);
        }

        $user = User::where('email', $email)->first();
        if ($user == null) {
            $user = User::create([
                'email' => $email["email"],
            ]);
        }

        if (!$board->subscribers()->where('id', $user->id)->exists()) {
            $board->subscribers()->attach($user->id);
        }

        $request->session()->flash('success', 'You have been subscribed to this board.');
        return redirect(route('boards.show', ['board' => $board->name]));
    }

    /**
     * Unsubscribes a user from the board - either from a signed URL in a GET request
     * or an authenticated user in a DELETE request.
     *
     * @param  \Illuminate\Http\Request  $request
     * @param  \App\Board                $board the board to subscribe to
     * @param  \App\User                 $user the user to unsubscribe
     * @return \Illuminate\Http\Response
     */
    public function destroy(Request $request, Board $board, User $user)
    {
        if (Auth::check()) {
            if (!isset($user->id)) {
                $user = Auth::user();
            }
            $this->authorize('delete', [BoardSubscription::class, $board, $user]);
        } elseif (!$request->hasValidSignature()) {
            abort(401);
        }

        $board->subscribers()->detach($user->id);

        $request->session()->flash('success', 'You have been unsubscribed from this board.');
        return redirect(route('boards.show', ['board' => $board->name]));
    }

    /**
     * Triggers an email to the requested email address with either a subscribe or an
     * unsubscribe link to the appropriate route.
     *
     * @param  \Illuminate\Http\Request  $request
     * @param  \App\Board                $board the board to subscribe to
     * @return \Illuminate\Http\Response
     */
    public function sendLink(Board $board, Request $request)
    {
        $validator = Validator::make(
            $request->all(),
            [
                'email' => 'required|email',
            ]
        );

        if ($validator->fails()) {
            return redirect(route('boards.subscribe', ['board' => $board->name]))
                      ->withErrors($validator)
                      ->withInput();
        }

        $subscribe = boolval($request->subscribe);
        $params = null;
        if ($subscribe) {
            $params = ['email' => $request->email, 'board' => $board->name];
            $route = 'subscriptions.add';
        } else {
            $user = User::where('email', $request->email)->first();
            if (($user != null) && $user->subscriptions()->where('board_id', $board->id)->exists()) {
                $params = ['user' => $user->id, 'board' => $board->name];
            }
            $route = 'subscriptions.destroy';
        }

        if ($params != null) {
            $link = URL::temporarySignedRoute($route, now()->addDays(1), $params);
            Mail::to($request->email)->send(new SubscriptionLink($board, $link, $subscribe));
        }

        $request->session()->flash('success', 'A link has been sent to your email address.');
        return redirect(route('boards.subscribe', ['board' => $board->name]));
    }
}
