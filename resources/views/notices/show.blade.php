@extends('boards.layout', ['title' => $notice->title, 'activeBoard' => $notice->board])

@section('subcontent')

  <h1 class="notice">{{ $notice->title }}</h1>
  <div class="notice">{!! clean($notice->body) !!}</div>

  {{-- <div class="card shadow mb-4 h-100">
    <div class="card-header py-3">
      <h6 class="m-0 font-weight-bold text-primary">{{ $notice->title }}</h6>
    </div>
    <div class="card-body">
      {!! clean($notice->body) !!}
    </div>
  </div> --}}

  @if($notice->expired)
  <div class="row mb-4">
    <div class="col">
      <div class="card bg-danger text-white shadow">
        <div class="card-body font-weight-bold">
          This notice has now expired and will not be shown on the Notice Board or Newsfeed.
        </div>
      </div>
    </div>
  </div>
  @endif

  @foreach($notice->messages as $follow_up)

    <div class="card shadow mb-4 h-100">
      <div class="card-header py-3 d-flex flex-row align-items-center justify-content-between">
        <h6 class="m-0 text-primary">
          <span class="font-weight-bold"><i class="fas fa-reply"></i> Update:</span>
          {{ $follow_up->createdBy->name }}, {!! \App\Helpers\TowerBoardUtils::dateToUserStr($follow_up->created_at) !!}
        </h6>
        <div class="dropdown no-arrow">
          <a class="dropdown-toggle" href="#" role="button" id="dropdownMenuLink" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
            <i class="fas fa-ellipsis-v fa-sm fa-fw text-gray-400"></i>
          </a>
          <div class="dropdown-menu dropdown-menu-right shadow animated--fade-in" aria-labelledby="dropdownMenuLink">
            <div class="dropdown-header">Actions:</div>
            @can('update', $notice)
              <div class="dropdown-divider"></div>
              <a class="dropdown-item" href="#" onclick="toggleEditMessage({{ $follow_up->id }}); return false;">Edit</a>
              <form method="POST" action="{{ route('messages.destroy', [ 'board' => $notice->board, 'notice' => $notice, 'message' => $follow_up ]) }}" style="display: inline">
                  @method("DELETE")
                  @csrf
                  <button type="submit" class="dropdown-item" onclick="return confirm('Are you sure?')">Delete</button>
              </form>
            @endcan
          </div>
        </div>
      </div>
      <div class="card-body" id="show-message-{{ $follow_up->id }}">
        {!! clean($follow_up->message) !!}
      </div>
      <div class="card-body collapse" id="edit-message-{{ $follow_up->id }}">
          <form method="POST" action="{{ route('messages.update', ['board' => $notice->board, 'notice' => $notice, 'message' => $follow_up]) }}" id="edit-message-form" novalidate>
            @csrf
            @method("PATCH")
            <div class="form-group row">
              <label for="message" class="col-md-4 col-form-label text-md-right">Message</label>
              <div class="col-md-6">
                <textarea id="message" name="message" rows="5" class="form-control @error('message') is-invalid @enderror" required>{{ old('message', $follow_up->message) }}</textarea>
                <div class="invalid-feedback" role="alert">@error('message') {{ $message }} @else Please enter your update. @enderror</div>
              </div>
            </div>

            <div class="form-group row mb-0">
              <div class="col-md-6 offset-md-4">
                <a href="#" class="btn btn-secondary btn-icon-split" onclick="toggleViewMessage({{ $follow_up->id }}); return false">
                  <span class="icon text-white-50"><i class="fas fa-times"></i></span>
                  <span class="text">Cancel</span>
                </a>
                <button type="submit" class="btn btn-success btn-icon-split">
                  <span class="icon text-white-50"><i class="fas fa-check"></i></span>
                  <span class="text">Update</span>
                </button>
              </div>
            </div>

          </form>
        </div>

    </div>

  @endforeach

  @can('update', $notice)

    <div class="card shadow mb-4">
      <a href="#messageForm" class="d-block card-header py-3" data-toggle="collapse" role="button" aria-expanded="false" aria-controls="messageForm">
        <h6 class="m-0 text-primary">
          <span class="font-weight-bold"><i class="fas fa-reply"></i> Post New Update</span>
        </h6>
      </a>
      <div class="collapse" id="messageForm">
        <div class="card-body">
          <form method="POST" action="{{ route('messages.store', ['board' => $notice->board, 'notice' => $notice]) }}" id="add-message-form" novalidate>
            @csrf
            <div class="form-group row">
              <label for="message" class="col-md-4 col-form-label text-md-right">Message</label>
              <div class="col-md-6">
                <textarea id="message" name="message" rows="5" class="form-control @error('message') is-invalid @enderror" required>{{ old('message') }}</textarea>
                <div class="invalid-feedback" role="alert">@error('message') {{ $message }} @else Please enter your update. @enderror</div>
              </div>
            </div>

            <div class="form-group row mb-0">
              <div class="col-md-6 offset-md-4">
                <button type="submit" class="btn btn-success btn-icon-split">
                  <span class="icon text-white-50"><i class="fas fa-check"></i></span>
                  <span class="text">Post</span>
                </button>
              </div>
            </div>

          </form>
        </div>

      </div>
    </div>

  @endcan

  @if(!$notice->expired && $notice->replyTo != null)
    <div class="card shadow mb-4">
      <a href="#replyForm" class="d-block card-header py-3" data-toggle="collapse" role="button" aria-expanded="false" aria-controls="replyForm">
        <h6 class="m-0 font-weight-bold text-primary"><i class="far fa-envelope"></i> Send Reply</h6>
      </a>
      <div class="collapse" id="replyForm">
        <div class="card-body">
          @auth
            <form method="POST" action="{{ route('notices.reply', ['board' => $notice->board->name, 'notice' => $notice->id]) }}" id="reply-form" novalidate>
              @csrf
              <div class="form-group row">
                <label for="reply_to" class="col-md-4 col-form-label text-md-right">To</label>
                <div class="col-md-6">
                    <span class="form-control">{{ $notice->replyTo->name }}</span>
                    <small>Please Note: when you reply your email address will be shared with this user.</small>
                </div>
              </div>

              <div class="form-group row">
                <label for="message" class="col-md-4 col-form-label text-md-right">Message</label>
                <div class="col-md-6">
                  <textarea id="message" name="message" rows="5" class="form-control @error('message') is-invalid @enderror" required>{{ old('message') }}</textarea>
                  <div class="invalid-feedback" role="alert">@error('message') {{ $message }} @else Please enter your reply. @enderror</div>
                </div>
              </div>

              <div class="form-group row mb-0">
                <div class="col-md-6 offset-md-4">
                  <button type="submit" class="btn btn-success btn-icon-split">
                    <span class="icon text-white-50"><i class="fas fa-envelope"></i></span>
                    <span class="text">Send</span>
                  </button>
                </div>
              </div>

            </form>
          @else
            <p>To send a reply you must <a href="{{ route('login') }}">log in</a>.</p>
          @endauth
        </div>
      </div>
    </div>
  @endif

  <div class="row">
    <div class="col-xl-3 col-md-6 mb-4">
      <div class="card border-left-primary shadow h-100 py-2">
        <div class="card-body">
          <div class="row no-gutters align-items-center">
            <div class="col mr-2">
              <div class="text-xs font-weight-bold text-primary text-uppercase mb-1">Posted by</div>
              <div class="h5 mb-0 text-gray-800">
                  {{ $notice->createdBy->name }}
              </div>
            </div>
            <div class="col-auto">
              <i class="fas fa-user fa-2x text-gray-900"></i>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div class="col-xl-3 col-md-6 mb-4">
      <div class="card border-left-warning shadow h-100 py-2">
        <div class="card-body">
          <div class="row no-gutters align-items-center">
            <div class="col mr-2">
              <div class="text-xs font-weight-bold text-warning text-uppercase mb-1">Date</div>
              <div class="h5 mb-0 text-gray-800">
                  {!! \App\Helpers\TowerboardUtils::dateToUserStr($notice->created_at) !!}
              </div>
            </div>
            <div class="col-auto">
              <i class="far fa-calendar-alt fa-2x text-gray-900"></i>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div class="col-xl-3 col-md-6 mb-4">
      <div class="card border-left-danger shadow h-100 py-2">
        <div class="card-body">
          <div class="row no-gutters align-items-center">
            <div class="col mr-2">
              <div class="text-xs font-weight-bold text-danger text-uppercase mb-1">Visibility</div>
              <div class="h5 mb-0 text-gray-800">
                  {{ ucwords(str_plural($notice->distribution->description)) }}
              </div>
            </div>
            <div class="col-auto">
              <i class="far fa-eye fa-2x text-gray-900"></i>
            </div>
          </div>
        </div>
      </div>
    </div>
    @isset($notice->expires)
      <div class="col-xl-3 col-md-6 mb-4">
        <div class="card border-left-success shadow h-100 py-2">
          <div class="card-body">
            <div class="row no-gutters align-items-center">
              <div class="col mr-2">
                <div class="text-xs font-weight-bold text-success text-uppercase mb-1">
                  @if($notice->expired) Expired @else Expires @endif
                </div>
                <div class="h5 mb-0 text-gray-800">
                    {!! \App\Helpers\TowerboardUtils::dateToUserStr($notice->expires) !!}
                </div>
              </div>
              <div class="col-auto">
                <i class="far fa-clock fa-2x text-gray-900"></i>
              </div>
            </div>
          </div>
        </div>
      </div>
    @endisset
  </div>

  <a href="{{ route('boards.show', ['board' => $notice->board]) }}" class="btn btn-secondary btn-icon-split">
    <span class="icon text-white-50"><i class="fas fa-arrow-left"></i></span>
    <span class="text">Back</span>
  </a>

  @can('update', $notice)

    <a href="{{ route('notices.edit', [ 'board' => $notice->board->name, 'notice' => $notice->id ]) }}" class="btn btn-primary btn-icon-split">
      <span class="icon text-white-50"><i class="fas fa-edit"></i></span>
      <span class="text">Edit</span>
    </a>

    <form method="POST" action="{{ route('notices.destroy', [ 'board' => $notice->board->name, 'notice' => $notice->id ]) }}" style="display: inline">
        @method("DELETE")
        @csrf
        <button type="submit" class="btn btn-danger btn-icon-split" onclick="return confirm('Are you sure?')">
          <span class="icon text-white-50"><i class="fas fa-trash"></i></span>
          <span class="text">Delete</span>
        </button>
     </form>

  @endcan

@endsection

@section('pagescripts')
<script>
  $('#reply-form,#add-message-form,#edit-message-form').on('submit', function(event) {
    if (this.checkValidity() === false) {
      event.preventDefault();
      event.stopPropagation();
    }
    this.classList.add('was-validated');
  });

function toggleEditMessage(id) {
  $('#edit-message-' + id).show();
  $('#show-message-' + id).hide();
}

function toggleViewMessage(id) {
  $('#edit-message-' + id).hide();
  $('#show-message-' + id).show();
}
</script>
@endsection
