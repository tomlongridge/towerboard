@extends('layouts.app', ['title' => $board->name])

@section('content')

    <div class="container-fluid">
        <div class="row subscribe">
            <div class="col">
                @if($board->tower)
                    <p>@include('macros.tower', ['tower' => $board->tower])</p>
                @endif
            </div>
            <div class="col" style="text-align: right">

                @subscriber($board)
                    You are a {{ $board->getSubscription()->type->description }} of this board.
                @endsubscriber

                @section('subscribe')
                    <input type="submit" class="btn btn-primary" value="Subscribe" />
                @endsection
                @section('unsubscribe')
                    <input type="submit" class="btn btn-primary" value="Unsubscribe" />
                @endsection
                @include('macros.subscribe', [ 'board' => $board, 'user' => null])

            </div>
        </div>
        <div class="row board-nav">
            <div class="col {{ Route::currentRouteName() == 'boards.show' ? 'selected' : '' }}"><a href="{{ route('boards.show', ['board' => $board->name]) }}">Notices</a></div>
            <div class="col {{ Route::currentRouteName() == 'boards.committee' ? 'selected' : '' }}"><a href="{{ route('boards.committee', ['board' => $board->name]) }}">Committee</a></div>
            <div class="col {{ Route::currentRouteName() == 'boards.details' ? 'selected' : '' }}">
                <a href="{{ route('boards.details', ['board' => $board->name]) }}">
                    {{ \App\Enums\BoardType::getDescription($board->type) }} Details
                </a>
            </div>
            <div class="col {{ Route::currentRouteName() == 'boards.members' ? 'selected' : '' }}"><a href="{{ route('boards.members', ['board' => $board->name]) }}">Members</a></div>
            <div class="col {{ Route::currentRouteName() == 'boards.contact' ? 'selected' : '' }}"><a href="{{ route('boards.contact', ['board' => $board->name]) }}">Contact</a></div>
        </div>
    </div>

    @yield('subcontent')

@endsection
