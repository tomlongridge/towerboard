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
use Carbon\Carbon;
use Illuminate\Support\Facades\Mail;
use App\Mail\UnsubscribeLink;
use Illuminate\Contracts\Encryption\DecryptException;
use Illuminate\Support\Facades\URL;

class SubscriptionController extends Controller
{
    /**
     * Store a newly created resource in storage.
     *
     * @param  \Illuminate\Http\Request  $request
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

    public function add(Board $board, EmailListRequest $request)
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
     * Remove the specified resource from storage.
     *
     * @param  \App\BoardSubscription  $boardSubscription
     * @return \Illuminate\Http\Response
     */
    public function destroy(Request $request, Board $board, User $user)
    {
        if ($request->method() == "GET") {
            if (!$request->hasValidSignature()) {
                abort(401);
            }
        } else {
            if (!isset($user->id)) {
                $user = Auth::user();
            }
            $this->authorize('delete', [BoardSubscription::class, $board, $user]);
        }
        $board->subscribers()->detach($user->id);

        $request->session()->flash('success', 'You have been unsubscribed from this board.');
        return redirect(route('boards.show', ['board' => $board->name]));
    }

    public function sendLink(Board $board, Request $request)
    {
        $validator = Validator::make(
            $request->all(),
            [
                'email' => 'required|email',
            ]
        );

        if ($validator->fails()) {
            return redirect(route('boards.unsubscribe', ['board' => $board->name]))
                      ->withErrors($validator)
                      ->withInput();
        }

        $user = User::where('email', $request->email)->first();
        if (($user != null) && $user->subscriptions()->where('board_id', $board->id)->exists()) {
            $unsubscribeLink =
                URL::temporarySignedRoute(
                    'subscriptions.destroy',
                    now()->addDays(1),
                    ['user' => $user->id, 'board' => $board->name]
                );
            Mail::to($request->email)->send(new UnsubscribeLink($board, $unsubscribeLink));
        }

        $request->session()->flash('success', 'Unsubscribe link sent to your email address.');
        return redirect(route('boards.unsubscribe', ['board' => $board->name]));
    }
}
