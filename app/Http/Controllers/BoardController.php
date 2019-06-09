<?php

namespace App\Http\Controllers;

use App\Board;

use Auth;
use Illuminate\Http\Request;
use App\Enums\SubscriptionType;

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
    public function store(Request $request)
    {
        $board = Board::create(
            $this->validateFields($request) +
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
        return view('boards.show', compact('board'));
    }

    public function committee(Board $board)
    {
        return view('boards.committee', compact('board'));
    }

    public function details(Board $board)
    {
        return view('boards.details', compact('board'));
    }

    public function contact(Board $board)
    {
        return view('boards.contact', compact('board'));
    }

    public function members(Board $board)
    {
        return view('boards.members', compact('board'));
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
    public function update(Request $request, Board $board)
    {
        $board->update($this->validateFields($request));

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

    private function validateFields($request)
    {
        return $request->validate([
            'name' => 'required',
            'tower_id' => 'nullable',
            'website_url' => 'nullable',
            'can_post' => 'nullable'
        ]);
    }
}
