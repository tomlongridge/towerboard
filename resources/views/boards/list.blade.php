@extends('layouts.app', ['title' => 'Boards'])

@section('content')

    <div id="boards-list">

        <h2>Search</h2>
        <input class="search" placeholder="search" />
        <input type="radio" name="type" id="type-tower" value="tower" /> Tower
        <input type="radio" name="type" id="type-guild" value="guild" /> Guild

        <h2>Boards</h2>
        <ul class="list">
        @foreach($boards as $board)
            <li data-type="{{ $board->tower ? 'tower' : 'guild' }}">
                <span class="tower-item">
                @if($board->tower)
                    @include('macros.tower', ['tower' => $board->tower, 'url' => route('boards.show', ['board' => $board->id])])
                @elseif($board->guild)
                    <a href="/boards/{{ $board->id }}">{{ $board->guild->name }}</a>
                    @else
                    <a href="/boards/{{ $board->id }}">{{ $board->name }}</a>
                @endif
                </span>
            </li>
        @endforeach
        </ul>

    </div>

    @auth
        <a class="btn btn-primary" id="menu-toggle" href="/boards/create">Create</a>
    @endauth

@endsection

@section('pagescripts')

    <script>
        var options = {
            valueNames: [ 'tower-item', { data: ['type'] } ]
        };
        var boardList = new List('boards-list', options);
        $('input[name=type]').change(function() {
            $boardType = $('input[name=type]:checked').val();
            boardList.filter(function(item) {
                console.log(item.values().type + " = " + $boardType);
                return $boardType === item.values().type;
            });
        });
    </script>

@endsection
