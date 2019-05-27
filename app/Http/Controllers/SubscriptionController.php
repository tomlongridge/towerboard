<?php

namespace App\Http\Controllers;

use App\Board;
use App\BoardSubscription;
use Auth;
use Illuminate\Http\Request;

class SubscriptionController extends Controller
{
    /**
     * Store a newly created resource in storage.
     *
     * @param  \Illuminate\Http\Request  $request
     * @return \Illuminate\Http\Response
     */
    public function store(Request $request, Board $board)
    {
        $board->subscribers()->attach(Auth::user()->id);
        return redirect(route('boards.show', [ 'board' => $board ]));
    }

    /**
     * Remove the specified resource from storage.
     *
     * @param  \App\BoardSubscription  $boardSubscription
     * @return \Illuminate\Http\Response
     */
    public function destroy(BoardSubscription $boardSubscription, Board $board)
    {
        $board->subscribers()->detach(Auth::user()->id);
        return redirect(route('boards.show', [ 'board' => $board ]));
    }

}
