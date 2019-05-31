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

Auth::routes(['verify' => true]);

Route::get('/', function () {
    return view('welcome');
})->name('home');

Route::resource('/boards', 'BoardController')->middleware('verified');
Route::resource('/api/guilds', 'GuildController')->middleware('verified');
Route::resource('/api/towers', 'TowerController')->middleware('verified');

Route::resource('/boards/{board}/notices', 'NoticeController')->middleware('verified');
Route::get('/boards/{board}/notices/{notice}/mail', 'NoticeController@mail')->middleware('verified');

Route::post('/boards/{board}/subscriptions', 'SubscriptionController@store')->name('subscriptions.store')->middleware('verified');
Route::delete('/boards/{board}/subscriptions', 'SubscriptionController@destroy')->name('subscriptions.destroy')->middleware('verified');

Route::get('/account', 'UserController@edit')->name('accounts.edit')->middleware('verified');
Route::patch('/account', 'UserController@update')->name('accounts.update')->middleware('verified');

Auth::routes();

Route::get('/home', 'HomeController@index')->name('home');
