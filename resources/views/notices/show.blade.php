@extends('layout')

@section('body')

    <h1 class="mt-4">{{ $notice->title }}</h1>

    <p>{{ $notice->body }}</p>

    <form method="POST" action="{{ route('notices.destroy', [ 'board' => $notice->board->id, 'notice' => $notice->id ]) }}">
        @method("DELETE")
        @csrf
        <input type="submit" class="btn btn-primary" value="Delete" />
    </form>

    <a href="{{ route('boards.show', [ 'board' => $notice->board->id ]) }}">Back</a>

@endsection
