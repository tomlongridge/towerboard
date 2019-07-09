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
          <div class="float-right">
            <a href="{{ route('register') }}" class="btn btn-success btn-icon-split">
              <span class="text">Register</span>
              <span class="icon text-white-50"><i class="fas fa-arrow-right"></i></span>
            </a>
          </div>
        </div>
      </div>

    </div>

    <div class="col-lg-8">

      <div class="card shadow mb-4">
        <div class="card-header py-3">
          <h6 class="m-0 font-weight-bold text-primary">Login</h6>
        </div>
        <div class="card-body px-5">

          <form method="POST" action="{{ route('login') }}" id="login-form" novalidate>
            @csrf
            <input type="hidden" name="returnUrl" value="{{ Request::query('returnUrl') }}" />

            <div class="form-group row">
              <label for="email" class="col-md-4 col-form-label text-md-right">Email Address</label>
              <div class="col-md-6">
                <input id="email" type="email" class="form-control @error('email') is-invalid @enderror"
                        name="email" value="{{ old('email') }}" required autocomplete="email" autofocus />
                <div class="invalid-feedback" role="alert">@error('email') {{ $message }} @else Please enter your email address.@enderror</div>
              </div>
            </div>

            <div class="form-group row">
              <label for="password" class="col-md-4 col-form-label text-md-right">Password</label>
              <div class="col-md-6">
                <input id="password" type="password" class="form-control @error('password') is-invalid @enderror"
                        name="password" required autocomplete="current-password">
                <div class="invalid-feedback" role="alert">@error('password') {{ $message }} @else Please enter your password.@enderror</div>
              </div>
            </div>

            <div class="form-group row">
              <div class="col-md-6 offset-md-4">
                <div class="form-check">
                  <input class="form-check-input" type="checkbox" name="remember" id="remember" {{ old('remember') ? 'checked' : '' }}>
                  <label class="form-check-label" for="remember">Remember me</label>
                </div>
              </div>
            </div>

            <div class="form-group row mb-0">
              <div class="col-md-8 offset-md-4">
                <button type="submit" class="btn btn-success btn-icon-split">
                  <span class="icon text-white-50"><i class="fas fa-check"></i></span>
                  <span class="text">Login</span>
                </button>
                <a class="btn btn-link" href="{{ route('password.request') }}">Forgotten your password?</a>
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
    $('#login-form').on('submit', function(event) {
      if (this.checkValidity() === false) {
        event.preventDefault();
        event.stopPropagation();
      }
      this.classList.add('was-validated');
    });
</script>
@endsection
