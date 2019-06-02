@extends('layouts.app', ['title' => $notice->title])

@section('content')

    <p>{{ $notice->body }}</p>

    <a href="{{ route('notices.edit', [ 'board' => $notice->board->id, 'notice' => $notice->id ]) }}" class="btn btn-primary">Edit</a>

    <form method="POST" action="{{ route('notices.destroy', [ 'board' => $notice->board->id, 'notice' => $notice->id ]) }}" style="display: inline">
        @method("DELETE")
        @csrf
        <input type="submit" class="btn btn-primary" value="Delete" />
    </form>

    <a href="{{ route('boards.show', [ 'board' => $notice->board->id ]) }}" class="btn btn-secondary">Back</a>

@endsection
