@extends('layouts.app', ['title' => 'Edit Notice'])

@section('content')

    <div class="container">
        <form method="POST" action="{{ route('notices.update', [ 'board' => $notice->board->name, 'notice' => $notice->id ]) }}">
            @method('PATCH')
            @csrf

            <div class="row">
                <label for="title">Title</label>
                <input type="text" class="form-control" id="title" name="title" placeholder="Title" value="{{ old('title', $notice->title) }}" />
            </div>
            <div class="row">
                <label for="body">Body</label>
                <textarea class="form-control" id="body" name="body">{{ old('body', $notice->body) }}</textarea>
            </div>
            <div class="row">
                <input type="submit" class="btn btn-primary" id="menu-toggle" value="Save" />
                &nbsp;
                <a href="{{ route('notices.show', [ 'board' => $notice->board->name, 'notice' => $notice->id ]) }}" class="btn btn-secondary">Back</a>
            </div>
        </form>
    </div>

    @if(!$errors->isEmpty())
        <ul class="alert alert-danger">
        @foreach($errors->all() as $error)
            <li>{{ $error }}</li>
        @endforeach
        </ul>
    @endif

@endsection
