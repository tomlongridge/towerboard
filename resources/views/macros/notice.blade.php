<div class="col-lg-6">
  <div class="card shadow mb-4">
    <div class="card-header py-3 d-flex flex-row align-items-center justify-content-between">
      <h6 class="m-0 font-weight-bold text-primary">
        @if(!(isset($hideBoardName) && $hideBoardName))
          <a href="{{ route('boards.show', ['board' => $notice->board->name]) }}">{{ $notice->board->readable_name }}</a>
        @endif
      </h6>
      <div class="dropdown no-arrow">
        <a class="dropdown-toggle" href="#" role="button" id="dropdownMenuLink" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
          <i class="fas fa-ellipsis-v fa-sm fa-fw text-gray-400"></i>
        </a>
        <div class="dropdown-menu dropdown-menu-right shadow animated--fade-in" aria-labelledby="dropdownMenuLink">
          <div class="dropdown-header">Actions:</div>
          <a class="dropdown-item" href="{{ route('notices.show', ['board' => $notice->board->name, 'notice' => $notice->id]) }}">View</a>
          @can('update', $notice)
            <div class="dropdown-divider"></div>
            <a class="dropdown-item" href="{{ route('notices.edit', [ 'board' => $notice->board->name, 'notice' => $notice->id ]) }}">Edit</a>
            <form method="POST" action="{{ route('notices.destroy', [ 'board' => $notice->board->name, 'notice' => $notice->id ]) }}" style="display: inline">
                @method("DELETE")
                @csrf
                <button type="submit" class="dropdown-item" onclick="return confirm('Are you sure?')">Delete</button>
            </form>
          @endcan
        </div>
      </div>
    </div>
    <div class="card-body">
      <h5>{{ $notice->title }}</h5>
      {!! str_limit(clean($notice->body), 500, '&hellip;</p>') !!}
      <div class="row">
        @if($notice->expires && $notice->expires->isPast())
          <div class="col bg-danger text-light py-2">
            <strong>Expired:</strong>
            {!! \App\Helpers\TowerboardUtils::dateToUserStr($notice->expires) !!}
          </div>
        @elseif(isset($notice->expires))
          @can('update', $notice)
            <div class="col py-2 bg-warning text-dark">
              <strong>Expires:</strong>
              {!! \App\Helpers\TowerboardUtils::dateToUserStr($notice->expires) !!}
            </div>
          @endcan
        @endif
      </div>
      <div class="row">
        <div class="col">
          Posted by
          <strong>{{ $notice->createdBy->name }}</strong>,
            {!! \App\Helpers\TowerboardUtils::dateToUserStr($notice->created_at) !!}
        </div>
        <div class="col text-right">
          &raquo; <a href="{{ route('notices.show', ['board' => $notice->board->name, 'notice' => $notice->id]) }}">Read More&hellip;</a>
        </div>
      </div>
    </div>
  </div>
</div>
