@extends('layouts.app')

@section('content')

    <h1 class="mt-4">Boards</h1>

    <ul>
    @foreach($boards as $board)
        <li><a href="/boards/{{ $board->id }}">{{ $board->name }}</a></li>
    @endforeach
    </ul>

    @auth
        <a class="btn btn-primary" id="menu-toggle" href="/boards/create">Create</a>
    @endauth

@endsection
