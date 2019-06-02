@if(isset($url))
    <a href="{{ $url }}"><strong>{{ $tower->town }}</strong></a>,
@else
    {{ $tower->town }},
@endif
{{ $tower->county }} ({{ $tower->country }}), {{ $tower->dedication }}
{{ $tower->area ? ', ' . $tower->area : '' }},
<strong>{{ $tower->num_bells }}</strong>
{{ $tower->weight ? ', ' . $tower->weight : '' }}
