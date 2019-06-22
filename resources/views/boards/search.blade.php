@extends('layouts.app', ['title' => 'Boards'])

@section('content')

    <div id="boards-list">

    <div class="card mb-4">
      <div class="card-header py-3">
        <h6 class="m-0 font-weight-bold text-primary">Filter</h6>
      </div>
      <div class="card-body row">
          <div class="col-12 col-md-6">
        <input class="search" id="board-name" class="form-control" style="width: 100%" placeholder="Tower, guild, branch name..." value="{{ request('q') }}" />
          </div>
          <div class="col-12 col-md-6">
        <select class="selectpicker" id="board-type">
            <option value="*">All Types</option>
            <option value="{{ \App\Enums\BoardType::getKey(\App\Enums\BoardType::TOWER) }}">Towers</option>
            <option value="{{ \App\Enums\BoardType::getKey(\App\Enums\BoardType::GUILD) }}">Guilds/Associations</option>
            <option value="{{ \App\Enums\BoardType::getKey(\App\Enums\BoardType::BRANCH) }}">Branches/Districts</option>
            <option value="">Other</option>
        </select>
    </div>
      </div>
    </div>

        <ul class="list">
        @foreach($boards as $board)
          <div class="card border-left-primary shadow h-100 my-4" data-type="{{ \App\Enums\BoardType::getKey($board->type) }}">
            <div class="card-body">
              <div class="row no-gutters align-items-center">
                <div class="col mr-2">
                  <span class="tower-item">
                      @include('macros.board', ['board' => $board, 'route' => 'boards.show'])
                  </span>
                </div>
                <div class="col-auto">
                  @include('macros.boardicon', ['board' => $board])
                </div>
              </div>
            </div>
          </div>
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
        $('#board-type').change(function() {
            var boardType = $('#board-type').val();
            boardList.filter(function(item) {
                if (boardType === "*") {
                    return true;
                } else {
                    return (boardType === '' ? null : boardType) === item.values().type;
                }
            });
        });
        boardList.search($('#board-name').val());
    </script>

@endsection
