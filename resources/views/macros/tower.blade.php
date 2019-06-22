@isset($tower)
  @isset($url)
      <a href="{{ $url }}"><strong>{{ $tower->town }}</strong></a>,
  @else
      {{ $tower->town }},
  @endisset
  {{ $tower->county }} ({{ $tower->country }}),
  <span class="text-nowrap">{{ $tower->dedication }}</span>
  <span class="text-nowrap">{{ $tower->area ? ', ' . $tower->area : '' }}</span>@if(isset($full) && $full),
    <strong>{{ $tower->num_bells }}</strong>{{ $tower->weight ? ', ' . $tower->weight : '' }}
  @endif
@endisset
