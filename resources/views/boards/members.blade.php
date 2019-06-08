@extends('boards.layout')

@section('subcontent')

    <h2>Members</h2>

    @if(auth()->check() && ($board->owner->id == auth()->user()->id) && !$board->subscribers->isEmpty())
        <ul>
            @foreach($board->subscribers as $user)
                <li>
                    @section('unsubscribe')
                        <input type="submit" class="btn btn-primary" value="Unsubscribe" />
                    @endsection
                    @include('macros.subscribe', [ 'board' => $board, 'user' => $user ])
                    {{ $user->name }}
                    &lt;{{ TowerBoardUtils::obscureEmail($user->email) }}&gt;
                </li>
            @endforeach
        </ul>
    @else
        <p>{{ $board->subscribers()->count() }} members on Towerboard.</p>
    @endif

    @can('update', $board)
        <h2>Add Users</h2>
        <form method="POST" action="{{ route('subscriptions.email', ['board' => $board->name]) }}">
            @csrf
            <textarea name="emails" class="form-control">{{ old('emails') }}</textarea>
            <button type="submit" class="btn btn-primary">Add</button>
        </form>
    @endcan

    @if(!$errors->isEmpty())
        <ul class="alert alert-danger">
        @foreach($errors->all() as $error)
            <li>{{ $error }}</li>
        @endforeach
        </ul>
    @endif

@endsection
