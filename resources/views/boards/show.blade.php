@extends('boards.layout', ['title' => 'Edit Notice', 'activeBoard' => $board])

@section('subcontent')

    @foreach ($notices as $key => $notice)

      @if ($loop->iteration % 2 == 1)
        <div class="row">
      @endif

      @include('macros.notice', ['notice' => $notice, 'hideBoardName' => true])

      @if ($loop->iteration % 2 == 0)
        </div>
      @endif

    @endforeach

    @can('create', [\App\Notice::class, $board])
      @if ($notices->count() % 2 == 0)
        <div class="row">
      @endif
        <div class="col-lg-6">
          <div class="card shadow mb-4">
            <div class="card-header py-3 d-flex flex-row align-items-center justify-content-between">
              <div class="dropdown no-arrow">
                &nbsp;
              </div>
            </div>
            <div class="card-body text-center py-5">
                <a href="{{ route('notices.create', ['board' => $board ]) }}" class="btn btn-primary btn-icon-split">
                    <span class="icon text-white-50">
                      <i class="fas fa-plus"></i>
                    </span>
                    <span class="text">Add Notice</span>
                  </a>
            </div>
          </div>
        </div>

      @if ($notices->count() % 2 == 0)
        <div class="col-lg-6"></div>
      @endif
      </div>

    @else
      @if ($notices->count() % 2 == 1)
          <div class="col-lg-6"></div>
        </div>
      @endif
    @endcan

    @can('create', [\App\Notice::class, $board])
    @elseif($notices->isEmpty())
      <p>There are no notices on this board.</p>
    @endif

@endsection
