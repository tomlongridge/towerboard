<a href="{{ route("boards.show", ['board' => $board->name]) }}"><strong>{{ $board->name }}</strong></a>
@if($board->tower)
    &#8211;
    @include('macros.tower', ['tower' => $board->tower])
@endif
