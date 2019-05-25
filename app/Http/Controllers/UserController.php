<?php

namespace App\Http\Controllers;

use App\User;
use Illuminate\Http\Request;

use Auth;

class UserController extends Controller
{
    /**
     * Show the form for creating a new resource.
     *
     * @return \Illuminate\Http\Response
     */
    public function create()
    {
        return redirect(route('register'));
    }

    /**
     * Show the form for editing the specified resource.
     *
     * @return \Illuminate\Http\Response
     */
    public function edit()
    {
        $user = Auth::user();
        return view('users.edit', compact('user'));
    }

    /**
     * Update the specified resource in storage.
     *
     * @param  \Illuminate\Http\Request  $request
     * @param  \App\User  $user
     * @return \Illuminate\Http\Response
     */
    public function update(Request $request)
    {
        $user = Auth::user();
        $user->update($this->validateFields($request));
        return redirect(route('accounts.edit'));
    }

    /**
     * Remove the specified resource from storage.
     *
     * @param  \App\User  $user
     * @return \Illuminate\Http\Response
     */
    public function destroy(User $user)
    {
        //
    }

    private function validateFields($request)
    {
        return $request->validate(
            [ 'forename' => 'required',
              'surname' => 'required',
              'middle_initials' => '',
              'email' => 'required|unique:users,email,' . auth()->id() ]
        );
    }
}
