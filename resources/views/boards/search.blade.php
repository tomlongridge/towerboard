@extends('layouts.app', ['title' => 'Boards'])

@section('content')

    <div id="boards-list">

        <h2>Search</h2>

        <p>
            <input class="search" class="form-control" style="width: 300px" placeholder="Tower, guild, branch name..." />
        </p>

        <h3>Board Types</h3>
        <ul class="radio-list">
            <li>
                <input type="radio" name="type" id="board-type-all" value="*" checked />
                <label for="board-type-all">All</label>
            </li>
            <li>
                <input type="radio" name="type" id="board-type-towers" value="{{ \App\Enums\BoardType::getKey(\App\Enums\BoardType::TOWER) }}" />
                <label for="board-type-towers">Towers</label>
            </li>
            <li>
                <input type="radio" name="type" id="board-type-guilds" value="{{ \App\Enums\BoardType::getKey(\App\Enums\BoardType::GUILD) }}" />
                <label for="board-type-guilds">Guilds/Associations</label>
            </li>
            <li>
                <input type="radio" name="type" id="board-type-branches" value="{{ \App\Enums\BoardType::getKey(\App\Enums\BoardType::BRANCH) }}" />
                <label for="board-type-branches">Branches/Districts</label>
            </li>
            <li>
                <input type="radio" name="type" id="board-type-other" value="" />
                <label for="board-type-other">Other</label>
            </li>
        </ul>

        <hr />

        <ul class="list">
        @foreach($boards as $board)
            <li data-type="{{ \App\Enums\BoardType::getKey($board->type) }}">
                <span class="tower-item">
                    @if($board->tower)
                        @include('macros.tower', ['tower' => $board->tower, 'url' => route('boards.show', ['board' => $board->name])])
                    @else
                        <a href="{{ route("boards.show", ['board' => $board->name]) }}">{{ $board->name }}</a>
                    @endif
                    @if($board->isSubscribed(auth()->user()))
                        <i class="material-icons">star</i>
                    @endif
                </span>
            </li>
        @endforeach
        </ul>

    </div>

    @auth
        <a class="btn btn-primary" id="menu-toggle" href="{{ route('boards.create') }}">Create</a>
    @endauth

@endsection

@section('pagescripts')

    <script>
        var options = {
            valueNames: [ 'tower-item', { data: ['type'] } ]
        };
        var boardList = new List('boards-list', options);
        $('input[name=type]').change(function() {
            var boardType = $('input[name=type]:checked').val();
            boardList.filter(function(item) {
                if (boardType === "*") {
                    return true;
                } else {
                    return (boardType === '' ? null : boardType) === item.values().type;
                }
            });
        });
    </script>

@endsection
