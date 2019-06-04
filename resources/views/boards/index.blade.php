@extends('layouts.app', ['title' => 'Boards'])

@section('content')

    <h2>My Boards</h2>

    <ul class="list">
        @foreach($boards as $board)
            <li>
                @if($board->tower)
                    @include('macros.tower', ['tower' => $board->tower, 'url' => route('boards.show', ['board' => $board->name])])
                @else
                    <a href="{{ route("boards.show", ['board' => $board->name]) }}">{{ $board->name }}</a>
                @endif
            </li>
        @endforeach
    </ul>

@endsection
