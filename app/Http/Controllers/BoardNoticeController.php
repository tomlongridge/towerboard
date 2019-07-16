<?php

namespace App\Http\Controllers;

use App\Board;
use App\Enums\SubscriptionType;
use App\Notice;

use BenSampo\Enum\Traits\CastsEnums;

use App\Http\Requests\NoticeRequest;
use Illuminate\Support\Facades\Mail;
use App\Mail\NoticeReply;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Validator;
use Carbon\Carbon;
use Illuminate\Support\Facades\Notification;
use App\Notifications\NoticeCreated;
use App\Notifications\NoticeUpdated;

class BoardNoticeController extends Controller
{
    use CastsEnums;

    protected $enumCasts = [
        'distribution' => SubscriptionType::class
    ];

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

        return view("notices.edit", compact('board'));
    }

    /**
     * Store a newly created resource in storage.
     *
     * @param  \Illuminate\Http\Request  $request
     * @return \Illuminate\Http\Response
     */
    public function store(NoticeRequest $request, Board $board)
    {
        $this->authorize('create', [Notice::class, $board]);

        $notice = $board->addNotice($request->except(['files', 'notify']));

        if ($request->notify) {
            Notification::send(
                $notice->board->subscribers()->wherePivot('type', '>=', $notice->distribution->value)->get(),
                new NoticeCreated($notice)
            );
        }

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

        return view('notices.edit', compact('notice', 'board'));
    }

    /**
     * Update the specified resource in storage.
     *
     * @param  \Illuminate\Http\Request  $request
     * @param  \App\Notice  $notice
     * @return \Illuminate\Http\Response
     */
    public function update(NoticeRequest $request, Board $board, Notice $notice)
    {
        $this->authorize('update', [$notice, $board]);

        $notice->update($request->except(['files', 'notify']));

        if ($request->notify) {
            Notification::send(
                $notice->board->subscribers()->wherePivot('type', '>=', $notice->distribution->value)->get(),
                new NoticeUpdated($notice)
            );
        }

        return redirect(route('notices.show', ['board' => $board->name, 'notice' => $notice->id]));
    }

    /**
     * Remove the specified resource from storage.
     *
     * @param  \App\Notice  $notice
     * @return \Illuminate\Http\Response
     */
    public function archive(Board $board, Notice $notice)
    {
        $this->authorize('delete', [$notice, $board]);

        $notice->update([
            'deleted_at' => Carbon::now()
        ]);

        return redirect(route("notices.show", ['board' => $board->name, 'notice' => $notice->id]));
    }

    /**
     * Remove the specified resource from storage.
     *
     * @param  \App\Notice  $notice
     * @return \Illuminate\Http\Response
     */
    public function unarchive(Board $board, Notice $notice)
    {
        $this->authorize('delete', [$notice, $board]);

        $notice->update([
            'deleted_at' => null
        ]);

        return redirect(route("notices.show", ['board' => $board->name, 'notice' => $notice->id]));
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

    public function reply(Board $board, Notice $notice, Request $request)
    {
        $validator = Validator::make($request->all(), [
            'message' => 'required',
        ]);

        if ($validator->fails()) {
            return redirect(route('notices.show', ['board' => $board->name, 'notice' => $notice->id]))
                        ->withErrors($validator)
                        ->withInput();
        }

        if ($notice->replyTo()->exists()) {
            $user = auth()->user();
            Mail::to($notice->replyTo)->send(new NoticeReply($notice, $user, $request->message));
            $request->session()->flash('success', "Your reply has been sent to {$user->name}.");
        } else {
            $request->session()->flash('error', "No replies were requested for this notice.");
        }

        return redirect(route('notices.show', ['board' => $board->name, 'notice' => $notice->id]));
    }
}
