<?php

namespace App\Http\Controllers;

use App\Board;
use App\User;
use Auth;
use App\BoardSubscription;

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

        $board->subscribers()->attach(Auth::user()->id);
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
