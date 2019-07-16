<?php

namespace App\Http\Controllers;

use App\NoticeMessage;
use Illuminate\Http\Request;
use App\Board;
use App\Notice;
use App\User;
use Illuminate\Support\Facades\Validator;
use Illuminate\Support\Facades\Notification;
use App\Notifications\NoticeUpdated;

class NoticeMessageController extends Controller
{
    /**
     * Display a listing of the resource.
     *
     * @return \Illuminate\Http\Response
     */
    public function index(Board $board, Notice $notice)
    {
        return redirect(route("notices.show", ['board' => $board, 'notice' => $notice]));
    }

    /**
     * Show the form for creating a new resource.
     *
     * @return \Illuminate\Http\Response
     */
    public function create(Board $board, Notice $notice)
    {
        return redirect(route("notices.show", ['board' => $board, 'notice' => $notice]));
    }

    /**
     * Store a newly created resource in storage.
     *
     * @param  \Illuminate\Http\Request  $request
     * @return \Illuminate\Http\Response
     */
    public function store(Request $request, Board $board, Notice $notice)
    {
        $this->authorize('create', [NoticeMessage::class, $board, $notice]);

        $validator = Validator::make($request->all(), [
            'message' => 'required',
        ]);

        if ($validator->fails()) {
            return redirect(route('notices.show', ['board' => $board, 'notice' => $notice]))
                        ->withErrors($validator)
                        ->withInput();
        }

        NoticeMessage::create($request->merge([
            'notice_id' => $notice->id,
            'created_by' => auth()->id()
        ])->except('notify'));

        if ($request->notify) {
            Notification::send(
                $notice->board->subscribers()->wherePivot('type', '>=', $notice->distribution->value)->get(),
                new NoticeUpdated($notice)
            );
        }

        $request->session()->flash('success', "The message has been posted.");
        return redirect(route('notices.show', ['board' => $board, 'notice' => $notice]));
    }

    /**
     * Display the specified resource.
     *
     * @param  \App\NoticeMessage  $noticeMessage
     * @return \Illuminate\Http\Response
     */
    public function show(Request $request, Board $board, Notice $notice, NoticeMessage $message)
    {
        return redirect(route("notices.show", ['board' => $board, 'notice' => $notice]));
    }

    /**
     * Show the form for editing the specified resource.
     *
     * @param  \App\NoticeMessage  $noticeMessage
     * @return \Illuminate\Http\Response
     */
    public function edit(Request $request, Board $board, Notice $notice, NoticeMessage $message)
    {
        return redirect(route("notices.show", ['board' => $board, 'notice' => $notice]));
    }

    /**
     * Update the specified resource in storage.
     *
     * @param  \Illuminate\Http\Request  $request
     * @param  \App\NoticeMessage  $noticeMessage
     * @return \Illuminate\Http\Response
     */
    public function update(Request $request, Board $board, Notice $notice, NoticeMessage $message)
    {
        $validator = Validator::make($request->all(), [
            'message' => 'required',
        ]);

        if ($validator->fails()) {
            return response('Bad Request', 400);
        }

        $this->authorize('update', [$board, $notice, $message]);

        $message->update([
            'message' => $request->message,
        ]);

        if ($request->notify) {
            Notification::send(
                $notice->board->subscribers()->wherePivot('type', '>=', $notice->distribution->value)->get(),
                new NoticeUpdated($notice)
            );
        }

        $request->session()->flash('success', "The message has been updated.");
        return redirect(route('notices.show', ['board' => $board, 'notice' => $notice]));
    }

    /**
     * Remove the specified resource from storage.
     *
     * @param  \App\NoticeMessage  $noticeMessage
     * @return \Illuminate\Http\Response
     */
    public function destroy(Request $request, Board $board, Notice $notice, NoticeMessage $message)
    {
        $this->authorize('delete', [$board, $notice, $message]);

        $message->delete();

        $request->session()->flash('success', "The message has been removed.");
        return redirect(route('notices.show', ['board' => $board, 'notice' => $notice]));
    }
}
