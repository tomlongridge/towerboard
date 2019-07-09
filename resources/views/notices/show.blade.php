@extends('boards.layout', ['title' => $notice->title, 'activeBoard' => $notice->board])

@section('subcontent')

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

  <div class="card shadow mb-4 h-100">
    <div class="card-header py-3">
      <h6 class="m-0 font-weight-bold text-primary">{{ $notice->title }}</h6>
    </div>
    <div class="card-body">
      {!! clean($notice->body) !!}
    </div>
  </div>

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
              <i class="fas fa-user fa-2x text-gray-300"></i>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div class="col-xl-3 col-md-6 mb-4">
      <div class="card border-left-primary shadow h-100 py-2">
        <div class="card-body">
          <div class="row no-gutters align-items-center">
            <div class="col mr-2">
              <div class="text-xs font-weight-bold text-primary text-uppercase mb-1">Date</div>
              <div class="h5 mb-0 text-gray-800">
                  {!! \App\Helpers\TowerboardUtils::dateToUserStr($notice->created_at) !!}
              </div>
            </div>
            <div class="col-auto">
              <i class="far fa-calendar-alt fa-2x text-gray-300"></i>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div class="col-xl-3 col-md-6 mb-4">
      <div class="card border-left-primary shadow h-100 py-2">
        <div class="card-body">
          <div class="row no-gutters align-items-center">
            <div class="col mr-2">
              <div class="text-xs font-weight-bold text-primary text-uppercase mb-1">Visibility</div>
              <div class="h5 mb-0 text-gray-800">
                  {{ ucwords(str_plural($notice->distribution->description)) }}
              </div>
            </div>
            <div class="col-auto">
              <i class="far fa-eye fa-2x text-gray-300"></i>
            </div>
          </div>
        </div>
      </div>
    </div>
    @isset($notice->expires)
      <div class="col-xl-3 col-md-6 mb-4">
        <div class="card border-left-primary shadow h-100 py-2">
          <div class="card-body">
            <div class="row no-gutters align-items-center">
              <div class="col mr-2">
                <div class="text-xs font-weight-bold text-primary text-uppercase mb-1">
                  @if($notice->expired) Expired @else Expires @endif
                </div>
                <div class="h5 mb-0 text-gray-800">
                    {!! \App\Helpers\TowerboardUtils::dateToUserStr($notice->expires) !!}
                </div>
              </div>
              <div class="col-auto">
                <i class="far fa-clock fa-2x text-gray-300"></i>
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
  $('#reply-form').on('submit', function(event) {
    if (this.checkValidity() === false) {
      event.preventDefault();
      event.stopPropagation();
    }
    this.classList.add('was-validated');
  });
</script>
@endsection
