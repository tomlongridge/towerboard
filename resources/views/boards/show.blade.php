@extends('boards.layout')

@section('subcontent')

    @if(!$board->notices->isEmpty())
        <ul>
        @foreach ($board->notices as $notice)
            <li><a href="{{ route('notices.show', ['board' => $board->name, 'notice' => $notice->id]) }}">{{ $notice->title }}</a></li>
        @endforeach
        </ul>
    @else
        <p>There are no notices on this board.</p>
    @endif

    <hr />

    @can('create', [\App\Notice::class, $board])
        <h3>Add Notice</h3>
        <div class="container">
            <form method="POST" action="{{ route('notices.store', ['board' => $board->name]) }}">
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
