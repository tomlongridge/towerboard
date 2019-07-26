<div class="col-lg-6">
  <div class="card shadow mb-4">
    <div class="card-header py-3 d-flex flex-row align-items-center justify-content-between">
      <h6 class="m-0">
        @if(!(isset($hideBoardName) && $hideBoardName))
          <a href="{{ route('boards.show', ['board' => $notice->board->name]) }}">{{ $notice->board->readable_name }}</a>
        @else
          <strong>{{ $notice->createdBy->name }}</strong>,
            {!! \App\Helpers\Utils::dateToUserStr($notice->created_at) !!}
        @endif
      </h6>
      <div class="dropdown no-arrow">
        <a class="dropdown-toggle" href="#" role="button" id="dropdownMenuLink" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
          <i class="fas fa-ellipsis-v fa-sm fa-fw text-gray-400"></i>
        </a>
        <div class="dropdown-menu dropdown-menu-right shadow animated--fade-in" aria-labelledby="dropdownMenuLink">
          <div class="dropdown-header">Actions:</div>
          <a class="dropdown-item" href="{{ route('notices.show', ['board' => $notice->board->name, 'notice' => $notice->id]) }}">View</a>
          @if(isset($notice->replyTo) &&  !$notice->archived)
            <a class="dropdown-item" href="{{ route('notices.show', ['board' => $notice->board->name, 'notice' => $notice->id]) }}">Reply</a>
          @endif
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
    <div class="card-body notice">
      <h5>{{ $notice->title }}</h5>
      <p>{!! str_limit(strip_tags($notice->body), 500, '&hellip;</p>') !!}</p>
      <div class="row float-right pr-2">
        <a href="{{ route('notices.show', ['board' => $notice->board->name, 'notice' => $notice->id]) }}" class="btn btn-primary btn-icon-split">
          <span class="text">Read More</span>
          <span class="icon text-white-50"><i class="fas fa-arrow-right"></i></span>
        </a>
      </div>
    </div>
  </div>
</div>
