<?php

namespace App\Http\Controllers;

use App\Board;
use App\Notice;
use Illuminate\Http\Request;

class NoticeController extends Controller
{
    /**
     * Display a listing of the resource.
     *
     * @return \Illuminate\Http\Response
     */
    public function index(Board $board)
    {
        return redirect("/boards/$board->id");
    }

    /**
     * Show the form for creating a new resource.
     *
     * @return \Illuminate\Http\Response
     */
    public function create()
    {
        return redirect("/boards/$board->id");
    }

    /**
     * Store a newly created resource in storage.
     *
     * @param  \Illuminate\Http\Request  $request
     * @return \Illuminate\Http\Response
     */
    public function store(Request $request, Board $board)
    {
        $notice = $board->addNotice($this->validateFields($request));
        return redirect(route('boards.show', ['board' => $board->id]));
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
        $notice->update($this->validateFields($request));
        return redirect(route('notices.show', ['board' => $board->id, 'notice' => $notice->id]));
    }

    /**
     * Remove the specified resource from storage.
     *
     * @param  \App\Notice  $notice
     * @return \Illuminate\Http\Response
     */
    public function destroy(Board $board, Notice $notice)
    {
        $notice->delete();

        return redirect("/boards/$board->id");
    }

    private function validateFields($request)
    {
        return $request->validate(
            [ 'title' => 'required',
              'body' => 'required' ]
        );
    }
}
