@extends('layouts.app')

@section('content')

    <h1 class="mt-4">Create Board</h1>

    <div class="container">
        <form method="POST" action="/boards">
            @csrf

            <div class="row">
                <label for="name">Name</label>
                <input type="text" class="form-control" id="name" name="name" placeholder="My Tower" value="" />
            </div>
            <div class="row">
                <label for="name">Tower</label>
                <select class="form-control" id="tower" name="tower_id">
                        <option value="">Unattached</option>
                    @foreach (cache('towers') as $tower)
                        <option value="{{ $tower->id }}">{{ $tower->getName() }}</option>
                    @endforeach
                </select>
            </div>
            <div class="row">
                <input type="submit" class="btn btn-primary" id="menu-toggle" value="Create" />
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
