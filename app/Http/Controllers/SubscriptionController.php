<?php

namespace App\Http\Controllers;

use App\Board;
use App\User;
use App\BoardSubscription;
use App\Http\Requests\EmailListRequest;

use Auth;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Validator;
use App\Enums\SubscriptionType;

class SubscriptionController extends Controller
{
    /**
     * Store a newly created resource in storage.
     *
     * @param  \Illuminate\Http\Request  $request
     * @return \Illuminate\Http\Response
     */
    public function store(Board $board, User $user)
    {
        if (!isset($user->id)) {
            $user = Auth::user();
        }

        $this->authorize('create', [BoardSubscription::class, $board, $user]);

        $board->subscribers()->attach($user->id);
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

        foreach ($request->emails as $email) {
            $user = User::where('email', $email["email"])->first();
            if ($user == null) {
                $user = User::create([
                    'email' => $email["email"],
                    'forename' => $email["forename"],
                    'surname' => $email["surname"],
                ]);
            }

            if (!$board->subscribers()->where('id', $user->id)->exists()) {
                $board->subscribers()->attach($user->id);
            }
        }

        return back();
    }

    /**
     * Remove the specified resource from storage.
     *
     * @param  \App\BoardSubscription  $boardSubscription
     * @return \Illuminate\Http\Response
     */
    public function destroy(Board $board, User $user)
    {
        if (!isset($user->id)) {
            $user = Auth::user();
        }

        $this->authorize('delete', [BoardSubscription::class, $board, $user]);

        $board->subscribers()->detach($user->id);
        return back();
    }
}
