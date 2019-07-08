@extends('layouts.app')

@section('content')

  <div class="row">

    <div class="col-lg-4">

      <div class="card shadow mb-4">
        <div class="card-header py-3">
          <h6 class="m-0 font-weight-bold text-primary">Registering on Towerboard</h6>
        </div>
        <div class="card-body px-5">
          <p>
            You need an account on Towerboard in order to create a board; post to it; and manage the
            settings and members.
          </p>
          <p>
            You can browse boards and receive posts from Towerboard via email without an account. Or
            you can register for one later and more easily manage your preferences.
          </p>
        </div>
      </div>

      <div class="card shadow mb-4">
        <div class="card-header py-3">
          <h6 class="m-0 font-weight-bold text-primary">Already subscribed?</h6>
        </div>
        <div class="card-body px-5">
          <p>
            If you have subscribed via email &ndash; or someone else added your email address &ndash;
            you can setup your full account using the
            <a href="{{ route('password.request') }}">Reset Password</a> page.
          </p>
        </div>
      </div>

    </div>

    <div class="col-lg-8">

      <div class="card shadow mb-4">
        <div class="card-header py-3">
          <h6 class="m-0 font-weight-bold text-primary">Create Account</h6>
        </div>
        <div class="card-body px-5">

          <form method="POST" action="{{ route('register') }}" id="register-form" novalidate>
            @csrf

            <div class="form-group row">
              <label for="forename" class="col-md-4 col-form-label text-md-right">{{ __('Forename') }}</label>
              <div class="col-md-6">
                <input id="forename" type="text" class="form-control @error('forename') is-invalid @enderror"
                      name="forename" value="{{ old('forename') }}" required autocomplete="forename" autofocus />
                <div class="invalid-feedback" role="alert">@error('forename') {{ $message }} @else Please enter your given name / first name. @enderror</div>
              </div>
            </div>

            <div class="form-group row">
              <label for="middle_initials" class="col-md-4 col-form-label text-md-right">{{ __('Middle Initals') }}</label>
              <div class="col-md-6">
                <input id="middle_initials" type="text" class="form-control @error('middle_initials') is-invalid @enderror"
                      name="middle_initials" value="{{ old('middle_initials') }}" />
                <div class="invalid-feedback" role="alert">@error('middle_initials') {{ $message }} @enderror</div>
              </div>
            </div>

            <div class="form-group row">
              <label for="surname" class="col-md-4 col-form-label text-md-right">{{ __('Surname') }}</label>
              <div class="col-md-6">
                <input id="surname" type="text" class="form-control @error('surname') is-invalid @enderror"
                      name="surname" value="{{ old('surname') }}" required autocomplete="surname" />
                <div class="invalid-feedback" role="alert">@error('surname') {{ $message }} @else Please enter your last name / surname. @enderror</div>
              </div>
            </div>

            <div class="form-group row">
              <label for="email" class="col-md-4 col-form-label text-md-right">Email Address</label>
              <div class="col-md-6">
                <input id="email" type="email" class="form-control @error('email') is-invalid @enderror"
                      name="email" value="{{ old('email') }}" required autocomplete="email" />
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
                  <span class="text">Create Account</span>
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
    $('#register-form').on('submit', function(event) {
      if (this.checkValidity() === false) {
        event.preventDefault();
        event.stopPropagation();
      }
      this.classList.add('was-validated');
    });
</script>
@endsection
