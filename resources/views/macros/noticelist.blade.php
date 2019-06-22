@foreach ($notices as $key => $notice)

      @if ($loop->iteration % 2 == 1)
        <div class="row">
      @endif

        <div class="col-lg-6">
          <div class="card shadow mb-4">
            <div class="card-header py-3 d-flex flex-row align-items-center justify-content-between">
              <h6 class="m-0 font-weight-bold text-primary">
                @if(isset($hideBoardName) && $hideBoardName)
                  <a href="{{ route('boards.show', ['board' => $notice->board->name]) }}">{{ $notice->board->name }}</a>
                @endif
              </h6>
              <div class="dropdown no-arrow">
                <a class="dropdown-toggle" href="#" role="button" id="dropdownMenuLink" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                  <i class="fas fa-ellipsis-v fa-sm fa-fw text-gray-400"></i>
                </a>
                <div class="dropdown-menu dropdown-menu-right shadow animated--fade-in" aria-labelledby="dropdownMenuLink">
                  <div class="dropdown-header">Dropdown Header:</div>
                  <a class="dropdown-item" href="#">Action</a>
                  <a class="dropdown-item" href="#">Another action</a>
                  <div class="dropdown-divider"></div>
                  <a class="dropdown-item" href="#">Something else here</a>
                </div>
              </div>
            </div>
            <div class="card-body">
              <h5>{{ $notice->title }}</h5>
              {!! str_limit(clean($notice->body), 500, '&hellip;</p>') !!}
              <div class="row">
                <div class="col">
                  <strong>{{ $notice->createdBy->name }}, {{ (new \Carbon\Carbon($notice->created_at))->format('D j M') }}</strong>
                </div>
                <div class="col text-right">
                  &raquo; <a href="{{ route('notices.show', ['board' => $notice->board->name, 'notice' => $notice->id]) }}">Read More&hellip;</a>
                </div>
              </div>
            </div>
          </div>
        </div>

      @if ($loop->iteration % 2 == 0)
        </div>
      @endif

    @endforeach

    @if ($notices->count() % 2 == 1)
        <div class="col-lg-6"></div>
      </div>
    @endif
