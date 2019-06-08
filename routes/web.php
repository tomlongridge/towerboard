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

// Home
Route::get('/', function () {
    return view('welcome');
})->name('home');

// Authentication and accounts
Auth::routes(['verify' => true]);
Route::get('/account', 'UserController@edit')->name('accounts.edit')->middleware('verified');
Route::patch('/account', 'UserController@update')->name('accounts.update')->middleware('verified');

// API's
Route::resource('/api/towers', 'TowerController');

// Boards
Route::get('/boards/search', 'BoardController@search')->name('boards.search');
Route::resource('/boards', 'BoardController');
Route::get('/boards/{board}/committee', 'BoardController@committee')->name('boards.committee');
Route::get('/boards/{board}/details', 'BoardController@details')->name('boards.details');
Route::get('/boards/{board}/contact', 'BoardController@contact')->name('boards.contact');
Route::get('/boards/{board}/members', 'BoardController@members')->name('boards.members');

// Notices
Route::get('/notices', 'UserNoticeController@index')->name('users.notices');
Route::resource('/boards/{board}/notices', 'BoardNoticeController');
// Route::get('/boards/{board}/notices/{notice}/mail', 'BoardNoticeController@mail');

// Subscription
Route::post('/boards/{board}/subscriptions/users/{user?}', 'SubscriptionController@store')->name('subscriptions.store');
Route::delete('/boards/{board}/subscriptions/users/{user?}', 'SubscriptionController@destroy')
    ->name('subscriptions.destroy');
Route::patch('/boards/{board}/subscriptions/users/{user?}', 'SubscriptionController@update')
    ->name('subscriptions.update');
Route::post('/boards/{board}/subscriptions/emails', 'SubscriptionController@add')->name('subscriptions.email');
