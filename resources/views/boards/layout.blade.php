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

                @auth
                    @if (!$board->isSubscribed(auth()->user()))
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

            </div>
        </div>
        <div class="row board-nav">
            <div class="col {{ Route::currentRouteName() == 'boards.show' ? 'selected' : '' }}"><a href="{{ route('boards.show', ['board' => $board->id ]) }}">Notices</a></div>
            <div class="col {{ Route::currentRouteName() == 'boards.committee' ? 'selected' : '' }}"><a href="{{ route('boards.committee', ['board' => $board->id ]) }}">Committee</a></div>
            <div class="col {{ Route::currentRouteName() == 'boards.details' ? 'selected' : '' }}">
                <a href="{{ route('boards.details', ['board' => $board->id ]) }}">
                    {{ \App\Enums\BoardType::getDescription($board->type) }} Details
                </a>
            </div>
            <div class="col {{ Route::currentRouteName() == 'boards.contact' ? 'selected' : '' }}"><a href="{{ route('boards.contact', ['board' => $board->id ]) }}">Contact</a></div>
        </div>
    </div>

    @yield('subcontent')

@endsection
