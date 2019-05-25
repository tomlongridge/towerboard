@extends('layouts.app')

@section('content')

    <h1 class="mt-4">{{ $board->name }}</h1>

    <p>
        This board is managed by: {{ $board->owner->name }}.
    </p>

    <a class="btn btn-primary" href="{{ route('boards.edit',[ 'board' => $board->id ]) }}">Edit</a>

    <form method="POST" action="{{ route('boards.destroy', [ 'board' => $board->id ]) }}" style="display: inline">
        @method("DELETE")
        @csrf
        <input type="submit" class="btn btn-primary" value="Delete" />
    </form>

    <hr />

    @if(!$board->notices->isEmpty())
        <h2>Notices</h2>
        <ul>
        @foreach ($board->notices as $notice)
            <li><a href="{{ route('notices.show', ['board' => $board->id, 'notice' => $notice->id]) }}">{{ $notice->title }}</a></li>
        @endforeach
        </ul>
    @endif

    <h3>Add Notice</h3>
    <div class="container">
        <form method="POST" action="/boards/{{ $board->id }}/notices">
            @csrf

            <div class="row">
                <label for="title">Title</label>
                <input type="text" class="form-control" id="title" name="title" placeholder="Title" value="" />
            </div>
            <div class="row">
                <label for="body">Body</label>
                <textarea class="form-control" id="body" name="body"></textarea>
            </div>
            <div class="row">
                <input type="submit" class="btn btn-primary" id="menu-toggle" value="Create Notice" />
            </div>
        </form>
    </div>

@endsection
