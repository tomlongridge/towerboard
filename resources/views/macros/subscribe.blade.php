@auth
    @if (!$board->isSubscribed(isset($user) ? $user : auth()->user()))
        <form method="POST" action="{{ route('subscriptions.store', ['board' => $board->name, 'user' => isset($user) ? $user : null ]) }}" style="display: inline">
            @csrf
            @yield(isset($subscribe) ? $subscribe : 'subscribe')
        </form>
    @elseif(isset($user) && $user->id != auth()->id())
        <form method="POST" action="{{ route('subscriptions.destroy', ['board' => $board->name, 'user' => isset($user) ? $user : null ]) }}" style="display: inline">
            @csrf
            @method("DELETE")
            @yield(isset($unsubscribe) ? $unsubscribe : 'unsubscribe')
        </form>
    @endif
@endauth
