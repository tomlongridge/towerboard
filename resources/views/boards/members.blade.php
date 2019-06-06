@extends('boards.layout')

@section('subcontent')


    @if(!$board->subscribers->isEmpty() )
    <h2>Members</h2>
    <ul>
        @foreach($board->subscribers as $user)
            <li>
                @section('unsubscribe')
                    <input type="submit" class="btn btn-primary" value="Unsubscribe" />
                @endsection
                @include('macros.subscribe', [ 'board' => $board, 'user' => $user ])
                {{ $user->name }}
            </li>
        @endforeach
    </ul>
    @endif

    <h2>Add Users</h2>
    <form method="POST" action="{{ route('subscriptions.email', ['board' => $board->name]) }}">
        @csrf
        <textarea name="emails" class="form-control">{{ old('emails') }}</textarea>
        <button type="submit" class="btn btn-primary">Add</button>
    </form>

    @if(!$errors->isEmpty())
        <ul class="alert alert-danger">
        @foreach($errors->all() as $error)
            <li>{{ $error }}</li>
        @endforeach
        </ul>
    @endif

@endsection
