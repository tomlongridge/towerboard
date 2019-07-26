@extends('boards.layout', ['title' => $notice->title, 'activeBoard' => $notice->board])

@section('subcontent')

  @if($notice->archived)
  <div class="row mb-4">
    <div class="col">
      <div class="card bg-warning text-white shadow">
        <div class="card-body font-weight-bold">
          This notice has been archived.
        </div>
      </div>
    </div>
  </div>
  @endif

  <h1 class="notice">{{ $notice->title }}</h1>
  <div class="notice">{!! clean($notice->body) !!}</div>

  <div class="row my-4 ml-0">

    <div class="col">
      <a href="{{ route('boards.show', ['board' => $notice->board]) }}" class="btn btn-secondary btn-icon-split mr-2">
        <span class="icon text-white-50"><i class="fas fa-arrow-left"></i></span>
        <span class="text">Back</span>
      </a>
    </div>

    @can('update', $notice)

      <div class="col-auto float-right">
        <a href="{{ route('notices.edit', [ 'board' => $notice->board->name, 'notice' => $notice->id ]) }}" class="btn btn-primary btn-icon-split mr-2">
          <span class="icon text-white-50"><i class="fas fa-edit"></i></span>
          <span class="text">Edit</span>
        </a>

        <form method="POST" action="{{ route('notices.archive', [ 'board' => $notice->board->name, 'notice' => $notice->id ]) }}" style="display: inline">
          @csrf
          <button type="submit" class="btn btn-warning btn-icon-split mr-2">
            @if($notice->archived)
              <span class="icon text-white-50"><i class="far fa-folder"></i></span>
              <span class="text">Unarchive</span>
            @else
              @method("DELETE")
              <span class="icon text-white-50"><i class="far fa-folder"></i></span>
              <span class="text">Archive</span>
            @endif
          </button>
        </form>

        <form method="POST" action="{{ route('notices.destroy', [ 'board' => $notice->board->name, 'notice' => $notice->id ]) }}" style="display: inline">
          @method("DELETE")
          @csrf
          <button type="submit" class="btn btn-danger btn-icon-split mr-2" onclick="return confirm('Are you sure?')">
            <span class="icon text-white-50"><i class="fas fa-trash"></i></span>
            <span class="text">Delete</span>
          </button>
        </form>
      </div>

    @endcan

  </div>

  @foreach($notice->messages as $follow_up)

    <div class="card shadow mb-4 h-100">
      <div class="card-header py-3 d-flex flex-row align-items-center justify-content-between">
        <h6 class="m-0 text-primary">
          <span class="font-weight-bold"><i class="fas fa-reply"></i> Update:</span>
          {{ $follow_up->createdBy->name }}, {!! \App\Helpers\Utils::dateToUserStr($follow_up->created_at) !!}
        </h6>
        @if(!$notice->archived)
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
        @endif
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
              <div class="row">
                <div class="col">
                  <a href="#" class="btn btn-secondary btn-icon-split" onclick="toggleViewMessage({{ $follow_up->id }}); return false">
                    <span class="icon text-white-50"><i class="fas fa-times"></i></span>
                    <span class="text">Cancel</span>
                  </a>
                </div>
                <div class="col text-right">
                  <input type="checkbox" id="notify" name="notify" value="true" />
                  <label for="notify" class="pr-2">Send Notification</label>
                  <button type="submit" class="btn btn-success btn-icon-split">
                    <span class="icon text-white-50"><i class="fas fa-check"></i></span>
                    <span class="text">Update</span>
                  </button>
                </div>
              </div>
            </div>
          </div>

        </form>
      </div>

    </div>

  @endforeach

  @if(!$notice->archived)
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
              <div class="col-md-6 offset-md-4 text-right">
                <input type="checkbox" id="notify" name="notify" value="true" {{ old('notify', true) ? 'checked' : '' }} />
                <label for="notify" class="pr-2">Send Notification</label>
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
  @endif

  @if(!$notice->archived && $notice->replyTo != null)
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
      <div class="card border-left-success shadow h-100 py-2">
        <div class="card-body">
          <div class="row no-gutters align-items-center">
            <div class="col mr-2">
              <div class="text-xs font-weight-bold text-success text-uppercase mb-1">Posted On</div>
              <div class="h5 mb-0 text-gray-800">
                  {!! \App\Helpers\Utils::dateToUserStr($notice->created_at) !!}
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
    @isset($notice->deleted_at)
      <div class="col-xl-3 col-md-6 mb-4">
        <div class="card border-left-warning shadow h-100 py-2">
          <div class="card-body">
            <div class="row no-gutters align-items-center">
              <div class="col mr-2">
                <div class="text-xs font-weight-bold text-warning text-uppercase mb-1">
                  @if($notice->archived) Archived @else Expires @endif
                </div>
                <div class="h5 mb-0 text-gray-800">
                    {!! \App\Helpers\Utils::dateToUserStr($notice->deleted_at) !!}
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
