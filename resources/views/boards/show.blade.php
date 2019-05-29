@extends('layouts.app')

@section('content')

    <h1 class="mt-4">{{ $board->name }}</h1>
    @if($board->tower)
    <h2 class="mt-4">{{ $board->tower->getName() }}</h2>
    @endif

    <p>
        This board is managed by: {{ $board->owner->name }}.
    </p>

    @can('update', $board)
        <a class="btn btn-primary" href="{{ route('boards.edit',[ 'board' => $board->id ]) }}">Edit</a>

        <form method="POST" action="{{ route('boards.destroy', [ 'board' => $board->id ]) }}" style="display: inline">
            @method("DELETE")
            @csrf
            <input type="submit" class="btn btn-primary" value="Delete" />
        </form>
    @endcan

    @auth
        @if (!Auth::user()->isSubscribed())
            <form method="POST" action="{{ route('subscriptions.store', [ 'board' => $board->id ]) }}" style="display: inline">
                @csrf
                <input type="submit" class="btn btn-primary" value="Subscribe" />
            </form>
        @else
            <form method="POST" action="{{ route('subscriptions.destroy', [ 'board' => $board->id ]) }}" style="display: inline">
                @csrf
                @method("DELETE")
                <input type="submit" class="btn btn-primary" value="Unsubscribe" />
            </form>
        @endif
    @endauth

    <hr />

    <h2>Notices</h2>
    @if(!$board->notices->isEmpty())
        <ul>
        @foreach ($board->notices as $notice)
            <li><a href="{{ route('notices.show', ['board' => $board->id, 'notice' => $notice->id]) }}">{{ $notice->title }}</a></li>
        @endforeach
        </ul>
    @else
        <p>There are no notices on this board.</p>
    @endif

    @can('add-notice', $board)
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
    @endcan

@endsection
