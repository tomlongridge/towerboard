@extends('boards.layout', ['title' => 'Members', 'activeBoard' => $board])

@section('subcontent')

  <div class="row">
    <div class="col-xl-3 col-md-6 mb-4">
      <div class="card border-left-primary shadow h-100 py-2">
        <div class="card-body">
          <div class="row no-gutters align-items-center">
            <div class="col mr-2">
              <div class="text-xs font-weight-bold text-primary text-uppercase mb-1">Members</div>
              <div class="h5 mb-0 font-weight-bold text-gray-800">
                  {{ $board->members->count() }}
              </div>
            </div>
            <div class="col-auto">
              <i class="fas fa-user-friends fa-2x text-gray-300"></i>
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
              <div class="text-xs font-weight-bold text-primary text-uppercase mb-1">Subscribers</div>
              <div class="h5 mb-0 font-weight-bold text-gray-800">
                  {{ $board->subscribers->count() - $board->members->count() }}
              </div>
            </div>
            <div class="col-auto">
              <i class="fas fa-chalkboard-teacher fa-2x text-gray-300"></i>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div class="col-xl-6 col-md-12 mb-4">
      <div class="card border-left-primary shadow h-100 py-2">
        <div class="card-body">
          <div class="row no-gutters align-items-center">
            <div class="col mr-2">
              <div class="h5 mb-0 text-gray-800">
                  @subscriber($board)
                    You are {{ \App\Helpers\TowerBoardUtils::strToNoun($board->getSubscription()->type->description) }} of this board
                  @else
                    You are not subscribed to this board
                  @endsubscriber
              </div>
            </div>
            <div class="col-auto">
                @admin($board)
                @else
                  @section('subscribe')
                    <button type="submit" class="btn btn-primary btn-icon-split">
                      <span class="icon text-white-50"><i class="fas fa-star"></i></span>
                      <span class="text">Subscribe</span>
                    </button>
                  @endsection
                  @section('unsubscribe')
                    <button type="submit" class="btn btn-primary btn-icon-split">
                      <span class="icon text-white-50"><i class="far fa-star"></i></span>
                      <span class="text">Unsubscribe</span>
                    </button>
                  @endsection
                  @include('macros.subscribe', [ 'board' => $board, 'user' => null])
                @endadmin
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>


  <div class="card shadow mb-4">
    <div class="card-header py-3">
      <h6 class="m-0 font-weight-bold text-primary">
        @admin($board)
          Members &amp; Subscribers
        @else
          Members
        @endadmin
      </h6>
    </div>
    <div class="card-body">
      @if(!$users->isEmpty())
        <div class="table-responsive">
          <table class="table table-bordered" id="member-table" width="100%" cellspacing="0">
            <thead>
              <tr>
                <th>Name</th>
                @admin($board)
                  <th>Email</th>
                @endadmin
                <th>Membership</th>
                @admin($board)
                  <th>Action</th>
                @endadmin
              </tr>
            </thead>
            <tbody>
              @foreach($users as $user)
                <tr>
                  <td>{{ $user->name }}</td>
                  @admin($board)
                    <td>{{ TowerBoardUtils::obscureEmail($user->email) }}</td>
                  @endadmin
                  <td>
                    @admin($board)
                      @if($user->id != auth()->id())
                          <form method="POST" action="{{ route('subscriptions.update', ['board' => $board, 'user' => $user]) }}" style="display: inline">
                              @csrf
                              @method('PATCH')
                              <select name="type" class="form-control" onchange="this.form.submit()">
                                  @foreach (\App\Enums\SubscriptionType::getInstances() as $type)
                                      <option
                                          value="{{ $type->value }}"
                                          {{ $type->key == $user->subscription->type->key ? 'selected' : ''}}>
                                          {{ ucwords($type->description) }}
                                      </option>
                                  @endforeach
                              </select>
                          </form>
                      @else
                        {{ ucwords($user->subscription->type->description) }}
                      @endif
                    @else
                      {{ ucwords($user->subscription->type->description) }}
                    @endadmin
                  </td>
                  @admin($board)
                    <td>
                      @section('inline-unsubscribe')
                          <button type="submit" class="btn btn-danger btn-icon-split">
                              <span class="icon text-white-50"><i class="fas fa-trash"></i></span>
                              <span class="text">Remove</span>
                            </button>
                      @endsection
                      @include('macros.subscribe', [ 'unsubscribe' => 'inline-unsubscribe', 'board' => $board, 'user' => $user ])
                    </td>
                  @endadmin
                </tr>
              @endforeach
            </tbody>
          </table>
        </div>
      @else
        There are no members/subscribers.
      @endif
    </div>
  </div>

@endsection

@section('pagescripts')
<script>
  $(document).ready(function() {
    $('#member-table').DataTable({
        "paging": true,
        "ordering": true,
        "info": false,
        "lengthMenu": [ [25, 50, -1], [25, 50, "All"] ],
        "columns": [
          null,
          null,
          @admin($board)
          { "orderable": false },
          { "orderable": false },
          @endadmin
        ]
    });
  });

</script>
@endsection
