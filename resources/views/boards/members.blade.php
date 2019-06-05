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

@endsection
