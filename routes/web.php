<?php

/*
|--------------------------------------------------------------------------
| Web Routes
|--------------------------------------------------------------------------
|
| Here is where you can register web routes for your application. These
| routes are loaded by the RouteServiceProvider within a group which
| contains the "web" middleware group. Now create something great!
|
*/

Auth::routes();


Route::get('/', function () {
    return view('welcome');
})->name('home');

Route::resource('/boards', 'BoardController');

Route::resource('/boards/{board}/notices', 'NoticeController');

Route::post('/boards/{board}/subscriptions', 'SubscriptionController@store')->name('subscriptions.store');
Route::delete('/boards/{board}/subscriptions', 'SubscriptionController@destroy')->name('subscriptions.destroy');

Route::get('/account', 'UserController@edit')->name('accounts.edit');
Route::patch('/account', 'UserController@update')->name('accounts.update');
