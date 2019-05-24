@extends('layout')

@section('body')

    <h1 class="mt-4">Create Board</h1>

    <form method="POST" action="/boards">
        @csrf

        <div class="row">
            <label for="name">Name</label>
            <input type="text" class="form-control" id="name" name="name" placeholder="My Tower" value="" />
        </div>
        <div class="row">
            <input type="submit" class="btn btn-primary" id="menu-toggle" value="Create" />
        </div>
    </form>

    @foreach($errors->all() as $error)
        {{ $error }}
    @endforeach


@endsection
