@auth
    @if (!$board->isSubscribed(auth()->user()))
        <form method="POST" action="{{ route('subscriptions.store', ['board' => $board->name]) }}" style="display: inline">
            @csrf
            @yield('subscribe')
        </form>
    @else
        <form method="POST" action="{{ route('subscriptions.destroy', ['board' => $board->name]) }}" style="display: inline">
            @csrf
            @method("DELETE")
            @yield('unsubscribe')
        </form>
    @endif
@endauth
