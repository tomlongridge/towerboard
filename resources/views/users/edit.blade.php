@extends('layouts.app', ['title' => 'Account Details'])

@section('content')
  <div class="container-fluid">
    <div class="row">
      <div class="col">
        <div class="card shadow mb-4">
          <div class="card-header py-3">
            <h6 class="m-0 font-weight-bold text-primary">Edit Account Details</h6>
          </div>
          <div class="card-body px-5">
            <form method="POST" action="{{ route('accounts.update') }}" id="account-form" novalidate>
              @method('PATCH')
              @csrf

              <div class="form-group row">
                <label for="forename" class="col-md-4 col-form-label text-md-right">Forename</label>
                <div class="col-md-6">
                  <input type="text"  class="form-control @error('forename') is-invalid @enderror"
                         id="forename" name="forename" value="{{ old('forename', $user->forename) }}" required autocomplete="forename" autofocus />
                  <div class="invalid-feedback" role="alert">@error('forename') {{ $message }} @else Please enter your given name / first name. @enderror</div>
                </div>
              </div>
              <div class="form-group row">
                <label for="middle_initials" class="col-md-4 col-form-label text-md-right">Middle Initials</label>
                <div class="col-md-6">
                  <input type="text" class="form-control @error('middle_initials') is-invalid @enderror"
                         id="middle_initials" name="middle_initials" value="{{ old('middle_initials', $user->middle_initials) }}" />
                  <div class="invalid-feedback" role="alert">@error('middle_initials') {{ $message }} @enderror</div>
                </div>
              </div>
              <div class="form-group row">
                <label for="surname" class="col-md-4 col-form-label text-md-right">Surname</label>
                <div class="col-md-6">
                  <input type="text"  class="form-control @error('surname') is-invalid @enderror"
                         id="surname" name="surname" value="{{ old('surname', $user->surname) }}" required autocomplete="surname" />
                  <div class="invalid-feedback" role="alert">@error('surname') {{ $message }} @else Please enter your last name / surname. @enderror</div>
                </div>
              </div>
              <div class="form-group row">
                <label for="name" class="col-md-4 col-form-label text-md-right">Email Address</label>
                <div class="col-md-6">
                  <input type="text" class="form-control @error('email') is-invalid @enderror"
                         id="email" name="email" value="{{ old('email', $user->email) }}" required autocomplete="email" />
                  <div class="invalid-feedback" role="alert">@error('email') {{ $message }} @else Please enter your email address. @enderror</div>
                </div>
              </div>

              <div class="form-group row mb-0">
                  <div class="col-md-6 offset-md-4">
                    <button type="submit" class="btn btn-success btn-icon-split">
                      <span class="icon text-white-50"><i class="fas fa-check"></i></span>
                      <span class="text">Update</span>
                    </button>
                  </div>
              </div>

            </form>
          </div>
        </div>
      </div>
    </div>
    <div class="row">
      <div class="col">
        <div class="card shadow mb-4">
          <div class="card-header py-3">
            <h6 class="m-0 font-weight-bold text-primary">Subscriptions</h6>
          </div>
          <div class="card-body px-5">
              @if(!$subscriptions->isEmpty())
                <div class="table-responsive">
                  <table class="table table-bordered" id="member-table" width="100%" cellspacing="0">
                    <thead>
                      <tr>
                        <th>Board</th>
                        <th>Membership Type</th>
                        <th>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      @foreach($subscriptions as $board)
                        <tr>
                          <td>{{ $board->readable_name }}</td>
                          <td>{{ ucwords($board->pivot->type->description) }}</td>
                          <td>
                            @if ($board->pivot->type->value == \App\Enums\SubscriptionType::ADMIN)
                              <button type="submit" class="btn btn-secondary btn-icon-split disabled"
                              data-toggle="tooltip" data-placement="right" title="Unsubscribe disabled for administrators">
                                <span class="icon text-white-50"><i class="fas fa-trash"></i></span>
                                <span class="text">Remove</span>
                              </button>
                            @else
                              @section('inline-unsubscribe')
                                <button type="submit" class="btn btn-danger btn-icon-split">
                                  <span class="icon text-white-50"><i class="fas fa-trash"></i></span>
                                  <span class="text">Remove</span>
                                </button>
                              @endsection
                              @include('macros.subscribe', [ 'unsubscribe' => 'inline-unsubscribe', 'board' => $board, 'user' => null ])
                            @endif
                          </td>
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
      </div>
    </div>
  </div>
@endsection

@section('pagescripts')
<script>
    $('#account-form').on('submit', function(event) {
      if (this.checkValidity() === false) {
        event.preventDefault();
        event.stopPropagation();
      }
      this.classList.add('was-validated');
    });
</script>
@endsection


