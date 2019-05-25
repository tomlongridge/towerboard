@extends('layout')

@section('body')

    <h1 class="mt-4">Edit Board</h1>

    <div class="container">
        <form method="POST" action="{{ route('boards.show', [ 'board' => $board->id ]) }}">
            @method('PATCH')
            @csrf

            <div class="row">
                <label for="name">Name</label>
                <input type="text" class="form-control" id="name" name="name" placeholder="My Tower" value="{{ $board->name }}" />
            </div>
            <div class="row">
                <input type="submit" class="btn btn-primary" id="menu-toggle" value="Save" />
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
