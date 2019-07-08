@extends('layouts.app')

@section('content')

  @include('macros.alert', ['key' => 'resent', 'content' => 'A fresh verification link has been sent to your email address.'])

  <div class="row justify-content-center">

    <div class="col-lg-6">

      <div class="card shadow mb-4">
        <div class="card-header py-3">
          <h6 class="m-0 font-weight-bold text-primary">Email Verification</h6>
        </div>
        <div class="card-body px-5">
          <p>
            In order to check that you own the email address you provided, we have sent an activation email
            to it. Please check your inbox and following the link provided to fully activate your account.
          </p>
          <p>
            If you did not receive the email, <a href="{{ route('verification.resend') }}">click here</a> to
            request another.
          </p>
        </div>
      </div>
    </div>
  </div>

@endsection
