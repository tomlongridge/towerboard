@extends('layouts.app', ['title' => $notice->title, 'activeBoard' => $notice->board])

@section('content')

  <div class="card border-left-primary shadow h-100 py-2 my-4">
    <div class="card-body">
      <div class="row no-gutters align-items-center">
        <div class="col mr-2">
          <div class="h5 mb-0 font-weight-bold text-gray-800">
            @include('macros.board', ['board' => $notice->board])
          </div>
        </div>
        <div class="col-auto">
          @include('macros.boardicon', ['board' => $notice->board])
        </div>
      </div>
    </div>
  </div>

  <div class="card shadow mb-4 h-100">
    <div class="card-header py-3">
      <h6 class="m-0 font-weight-bold text-primary">{{ $notice->title }}</h6>
    </div>
    <div class="card-body">
      <p>{!! clean($notice->body) !!}</p>
    </div>
  </div>

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
                <div class="text-xs font-weight-bold text-primary text-uppercase mb-1">Expires</div>
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
