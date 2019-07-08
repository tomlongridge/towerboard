@extends('boards.layout', ['title' => 'Unsubscribe', 'activeBoard' => $board])

@section('subcontent')

  @include('macros.alert', ['key' => 'status'])

  <div class="row">

    <div class="col-lg-4">

      <div class="card shadow mb-4">
        <div class="card-header py-3">
          <h6 class="m-0 font-weight-bold text-primary">Unsubscribing</h6>
        </div>
        <div class="card-body px-5">
          <p>
            If you would like to stop receiving emails from this board and already have a Towerboard
            account, the easiest way to unsubscribe is to login and visit the My Account page.
          </p>
          <p>
            Otherwise, use the form opposite to unsubscribe your email address. We'll send you a link
            to your email address (to confirm it's really you). If you wish to unsubscribe from
            all Towerboard boards, then please check the box and we'll take you off our list entirely.
          </p>
        </div>
      </div>

    </div>

    <div class="col-lg-8">

      <div class="card shadow mb-4">
        <div class="card-header py-3">
          <h6 class="m-0 font-weight-bold text-primary">Send Unsubscribe Link</h6>
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
