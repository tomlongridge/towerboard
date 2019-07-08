@extends('layouts.app')

@section('content')

  <div class="container-fluid">
    <div class="row justify-content-center">
      <div class="col-lg-8">
        <div class="card shadow mb-4">
          <div class="card-header py-3">
            <h6 class="m-0 font-weight-bold text-primary">Reset Password</h6>
          </div>
          <div class="card-body px-5">

            <form method="POST" action="{{ route('password.update') }}" id="reset-form" novalidate>
              @csrf
              <input type="hidden" name="token" value="{{ $token }}">

              <div class="form-group row">
                <label for="email" class="col-md-4 col-form-label text-md-right">Email Address</label>
                <div class="col-md-6">
                  <input id="email" type="email" class="form-control @error('email') is-invalid @enderror"
                        name="email" value="{{ $email ?? old('email') }}" required autocomplete="email" />
                  <div class="invalid-feedback" role="alert">@error('email') {{ $message }} @else Please enter your email address. @enderror</div>
                </div>
              </div>

              <div class="form-group row">
                <label for="password" class="col-md-4 col-form-label text-md-right">{{ __('Password') }}</label>
                <div class="col-md-6">
                  <input id="password" type="password" class="form-control @error('password') is-invalid @enderror"
                        name="password" required autocomplete="new-password" />
                  <div class="invalid-feedback" role="alert">@error('password') {{ $message }} @else Please enter a password. @enderror</div>
                  @error('password')
                  @else
                  <small>(Please make your password longer than 8 characters and contain at least one number and both uppercase and lowercase letters.)</small>
                  @enderror
                </div>
              </div>

              <div class="form-group row">
                <label for="password-confirm" class="col-md-4 col-form-label text-md-right">{{ __('Confirm Password') }}</label>
                <div class="col-md-6">
                  <input id="password-confirm" type="password" class="form-control" name="password_confirmation" required autocomplete="new-password" />
                  <div class="invalid-feedback" role="alert">@error('password') {{ $message }} @else Please confirm your password. @enderror</div>
                </div>
              </div>

              <div class="form-group row mb-0">
                <div class="col-md-6 offset-md-4">
                  <button type="submit" class="btn btn-success btn-icon-split">
                    <span class="icon text-white-50"><i class="fas fa-check"></i></span>
                    <span class="text">Save</span>
                  </button>
                </div>
              </div>

            </form>
          </div>
        </div>
      </div>
    </div>

@endsection

@section('pagescripts')
<script>
    $('#reset-form').on('submit', function(event) {
      if (this.checkValidity() === false) {
        event.preventDefault();
        event.stopPropagation();
      }
      this.classList.add('was-validated');
    });
</script>
@endsection
