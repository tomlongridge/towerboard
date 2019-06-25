@isset($route)
  <a href="{{ route($route, ['board' => $board->name]) }}">
@endisset
{{ $board->readable_name }}
@isset($route)
  </a>
@endisset
@if($board->tower)
    &#8211;
    @include('macros.tower', ['tower' => $board->tower, 'full' => isset($full) ? $full : 'true'])
@endif
