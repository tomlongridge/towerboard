@extends('layouts.app', ['title' => 'Boards'])

@section('content')

    <h2>My Boards</h2>

    <ul class="list">
        @foreach($boards as $board)
            <li>
                @include('macros.board', ['board' => $board])
            </li>
        @endforeach
    </ul>

@endsection
