<?php

namespace App\Http\Controllers;

use App\Board;
use App\Notice;
use App\Notifications\NoticeCreated;
use Illuminate\Http\Request;
use Notification;

class BoardNoticeController extends Controller
{
    /**
     * Display a listing of the resource.
     *
     * @return \Illuminate\Http\Response
     */
    public function index(Board $board)
    {
        return redirect(route("boards.show", ['board' => $board->name]));
    }

    /**
     * Show the form for creating a new resource.
     *
     * @return \Illuminate\Http\Response
     */
    public function create(Board $board)
    {
        $this->authorize('create', [Notice::class, $board]);

        return redirect(route("boards.show", ['board' => $board->name]));
    }

    /**
     * Store a newly created resource in storage.
     *
     * @param  \Illuminate\Http\Request  $request
     * @return \Illuminate\Http\Response
     */
    public function store(Request $request, Board $board)
    {
        $this->authorize('create', [Notice::class, $board]);

        $notice = $board->addNotice($this->validateFields($request));

        Notification::send($board->subscribers, new NoticeCreated($notice));

        return redirect(route('boards.show', ['board' => $board->name]));
    }

    /**
     * Display the specified resource.
     *
     * @param  \App\Notice  $notice
     * @return \Illuminate\Http\Response
     */
    public function show(Board $board, Notice $notice)
    {
        return view('notices.show', compact('notice'));
    }

    /**
     * Show the form for editing the specified resource.
     *
     * @param  \App\Notice  $notice
     * @return \Illuminate\Http\Response
     */
    public function edit(Board $board, Notice $notice)
    {
        $this->authorize('update', [$notice, $board]);

        return view('notices.edit', compact('notice'));
    }

    /**
     * Update the specified resource in storage.
     *
     * @param  \Illuminate\Http\Request  $request
     * @param  \App\Notice  $notice
     * @return \Illuminate\Http\Response
     */
    public function update(Request $request, Board $board, Notice $notice)
    {
        $this->authorize('update', [$notice, $board]);

        $notice->update($this->validateFields($request));
        return redirect(route('notices.show', ['board' => $board->name, 'notice' => $notice->id]));
    }

    /**
     * Remove the specified resource from storage.
     *
     * @param  \App\Notice  $notice
     * @return \Illuminate\Http\Response
     */
    public function destroy(Board $board, Notice $notice)
    {
        $this->authorize('delete', [$notice, $board]);

        $notice->delete();

        return redirect(route("boards.show", ['board' => $board->name]));
    }

    public function mail(Board $board, Notice $notice)
    {
        return new NoticeCreated($notice);
    }

    private function validateFields($request)
    {
        return $request->validate(
            [ 'title' => 'required',
              'body' => 'required' ]
        );
    }
}
