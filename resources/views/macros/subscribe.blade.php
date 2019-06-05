@auth
    @if (!$board->isSubscribed(isset($user) ? $user : auth()->user()))
        <form method="POST" action="{{ route('subscriptions.store', ['board' => $board->name, 'user' => isset($user) ? $user : null ]) }}" style="display: inline">
            @csrf
            @yield('subscribe')
        </form>
    @else
        <form method="POST" action="{{ route('subscriptions.destroy', ['board' => $board->name, 'user' => isset($user) ? $user : null ]) }}" style="display: inline">
            @csrf
            @method("DELETE")
            @yield('unsubscribe')
        </form>
    @endif
@endauth
