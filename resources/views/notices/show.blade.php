@extends('layouts.app', ['title' => $notice->title])

@section('content')

    <p>{{ $notice->body }}</p>
    <p>Posted by: {{ $notice->createdBy->name }}</p>

    @can('update', $notice)

        <a href="{{ route('notices.edit', [ 'board' => $notice->board->name, 'notice' => $notice->id ]) }}" class="btn btn-primary">Edit</a>

        <form method="POST" action="{{ route('notices.destroy', [ 'board' => $notice->board->name, 'notice' => $notice->id ]) }}" style="display: inline">
            @method("DELETE")
            @csrf
            <input type="submit" class="btn btn-primary" value="Delete" />
        </form>

    @endcan

    <a href="{{ route('boards.show', [ 'board' => $notice->board->name ]) }}" class="btn btn-secondary">Back</a>

@endsection
