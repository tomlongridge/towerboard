<?php

namespace App\Http\Controllers;

use App\Board;

use Auth;
use Illuminate\Http\Request;
use App\Enums\SubscriptionType;
use App\Http\Requests\BoardRequest;
use Illuminate\Support\Facades\Mail;
use App\Mail\BoardContactMessage;
use Illuminate\Support\Facades\Validator;

class BoardController extends Controller
{
    public function __construct()
    {
        $this->authorizeResource(Board::class, 'board');
    }

    /**
     * Display a listing of the resource.
     *
     * @return \Illuminate\Http\Response
     */
    public function index()
    {
        if (!Auth::guest()) {
            $boards = Auth::user()->subscriptions;
            return view('boards.index', compact('boards'));
        } else {
            return $this->search();
        }
    }

    public function search()
    {
        $boards = Board::orderBy('name')->get();
        return view('boards.search', compact('boards'));
    }

    /**
     * Show the form for creating a new resource.
     *
     * @return \Illuminate\Http\Response
     */
    public function create()
    {
        return view('boards.edit');
    }

    /**
     * Store a newly created resource in storage.
     *
     * @param  \Illuminate\Http\Request  $request
     * @return \Illuminate\Http\Response
     */
    public function store(BoardRequest $request)
    {
        $board = Board::create(
            $request->all() +
            ['created_by' => auth()->id()]
        );
        $board->subscribe(auth()->user(), SubscriptionType::ADMIN);
        return redirect(route('boards.details', ['board' => $board->name]));
    }

    /**
     * Display the specified resource.
     *
     * @param  \App\Board  $board
     * @return \Illuminate\Http\Response
     */
    public function show(Board $board)
    {
        $user = auth()->user();
        $notices = $board->getNotices($user && $user->can('update', $board));

        return view('boards.show', compact('board', 'notices'));
    }

    /**
     * Show the form for editing the specified resource.
     *
     * @param  \App\Board  $board
     * @return \Illuminate\Http\Response
     */
    public function edit(Board $board)
    {
        return view('boards.edit', compact('board'));
    }

    /**
     * Update the specified resource in storage.
     *
     * @param  \Illuminate\Http\Request  $request
     * @param  \App\Board  $board
     * @return \Illuminate\Http\Response
     */
    public function update(BoardRequest $request, Board $board)
    {
        $board->update($request->all());

        return redirect(route('boards.details', ['board' => $board->name]));
    }

    /**
     * Remove the specified resource from storage.
     *
     * @param  \App\Board  $board
     * @return \Illuminate\Http\Response
     */
    public function destroy(Board $board)
    {
        $board->delete();

        return redirect(route('boards.index'));
    }

    public function committee(Board $board)
    {
        $committee = $board->committee()->get();
        return view('boards.committee', compact('board', 'committee'));
    }

    public function details(Board $board)
    {
        return view('boards.details', compact('board'));
    }

    public function contact(Board $board)
    {
        return view('boards.contact', compact('board'));
    }

    public function contactSend(Request $request, Board $board)
    {
        $validator = Validator::make(
            $request->all(),
            [
                'message' => 'required',
                'g-recaptcha-response' => 'required|captcha'
            ],
            [
                'g-recaptcha-response.required' => "Please complete the anti-robot challenge.",
                'g-recaptcha-response.captcha' => "The anti-robot challenge was not successful."
            ]
        );

        if ($validator->fails()) {
            return redirect(route('boards.contact', ['board' => $board->name]))
                       ->withErrors($validator)
                       ->withInput();
        }

        Mail::to($board->contacts()->get())
              ->send(new BoardContactMessage($board, auth()->user(), $request->message));

        return redirect(route('boards.contact', ['board' => $board->name]))
                   ->with('success', 'Message sent to the board administrators');
    }

    public function members(Board $board)
    {
        $user = auth()->user();
        if ($user && $user->can('update', $board)) {
            $users = $board->subscribers;
        } else {
            $users = $board->members;
        }
        return view('boards.members', compact('board', 'users'));
    }

    public function addMembers(Board $board)
    {
        $this->authorize('update', $board);
        return view('boards.add-members', compact('board'));
    }

    public function subscribe(Board $board)
    {
        return view('boards.subscribe', compact('board'));
    }
}
