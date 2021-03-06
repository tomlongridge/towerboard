@extends('layouts.app')

@section('content')

  @include('macros.alert', ['key' => 'status'])

  <div class="row">

    <div class="col-lg-4">

      <div class="card shadow mb-4">
        <div class="card-header py-3">
          <h6 class="m-0 font-weight-bold text-primary">Forgotten your password?</h6>
        </div>
        <div class="card-body px-5">
          <p>
            Enter your email address is the form opposite and we'll send you a link to reset it.
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
            use this form to set your password and start setting up your full account.
          </p>
        </div>
      </div>

    </div>

    <div class="col-lg-8">

      <div class="card shadow mb-4">
        <div class="card-header py-3">
          <h6 class="m-0 font-weight-bold text-primary">Send Password Reset Link</h6>
        </div>
        <div class="card-body px-5">

          <form method="POST" action="{{ route('password.email') }}" id="reset-form" novalidate>
            @csrf

            <div class="form-group row">
                <label for="email" class="col-md-4 col-form-label text-md-right">Email Address</label>
                <div class="col-md-6">
                  <input id="email" type="email" class="form-control @error('email') is-invalid @enderror" name="email" value="{{ old('email') }}" required autocomplete="email" autofocus>
                  <div class="invalid-feedback" role="alert">@error('email') {{ $message }} @else Please enter your email address.@enderror</div>
                  <small>If you email address is not found, <a href="{{ route('register') }}">click here</a> to register for a new account.</small>
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
