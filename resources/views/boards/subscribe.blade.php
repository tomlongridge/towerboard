@extends('boards.layout', ['title' => 'Unsubscribe', 'activeBoard' => $board])

@section('subcontent')

  @include('macros.alert', ['key' => 'status'])

  <div class="row">

    <div class="col-lg-4">

      <div class="card shadow mb-4">
        <div class="card-header py-3">
          <h6 class="m-0 font-weight-bold text-primary">Do you have an account?</h6>
        </div>
        <div class="card-body px-5">
          <p>
            The easiest way to manage the emails that your receive is to
            <a href="{{ route('register') }}">create a {{  config('app.name') }} account</a>,
            login and choose the boards that you wish to subscribe to or visit the My Account page to
            manage your exising subscriptions.
            If you have been receiving emails from {{  config('app.name') }} but have not set a password (or cannot
            remember it), then you can reset it <a href="{{ route('password.request') }}">here</a>.
          </p>
          <p>
            Otherwise, use the forms below to manually subscribe or unsubscribe your email address.
            We'll send you a link to your email address (to confirm it's really you) that will add or
            remove your email address from our list for this board.
          </p>
        </div>
      </div>

    </div>

    <div class="col-lg-8">

      <div class="card shadow mb-4">
        <div class="card-header py-3">
          <h6 class="m-0 font-weight-bold text-primary">Send Link</h6>
        </div>
        <div class="card-body px-5">

          <form method="POST" action="{{ route('subscriptions.link', ['board' => $board]) }}" id="reset-form" novalidate>
            @csrf

            <div class="form-group row">
                <label for="email" class="col-md-4 col-form-label text-md-right">Email Address</label>
                <div class="col-md-6">
                  <input id="email" type="email" class="form-control @error('email') is-invalid @enderror" name="email" value="{{ old('email') }}" required autocomplete="email" autofocus>
                  <div class="invalid-feedback" role="alert">@error('email') {{ $message }} @else Please enter your email address.@enderror</div>
                </div>
            </div>

            <div class="form-group row mb-0">
              <div class="col-md-6 offset-md-4">
                <button type="submit" name="subscribe" value="0" class="btn btn-secondary btn-icon-split">
                  <span class="icon text-white-50"><i class="far fa-star"></i></span>
                  <span class="text">Unsubscribe</span>
                </button>
                <button type="submit" name="subscribe" value="1" class="btn btn-success btn-icon-split">
                  <span class="icon text-white-50"><i class="fas fa-star"></i></span>
                  <span class="text">Subscribe</span>
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
